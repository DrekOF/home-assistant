"""
Nombre: test_sesion.py
Descripción: Pruebas de la sesión de la web y del primer administrador: contrato de iniciarSesion, verSesion y cerrarSesion, RNF-02 · C2 y RNF-02 · C5.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import time
from uuid import uuid4

import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner, URLSafeTimedSerializer
from sqlalchemy import Connection, Engine, text

from accesia.config import configuracion
from accesia.main import preparar_arranque
from accesia.sesion import COOKIE, DURACION_S, SAL, crear_primer_administrador

# Todas las rutas de B1 que piden sesión (openapi.yaml: security sesion).
ID = str(uuid4())
RUTAS_CON_SESION = [
    ("GET", "/api/v1/sesion"),
    ("GET", "/api/v1/personas"),
    ("POST", "/api/v1/personas"),
    ("GET", f"/api/v1/personas/{ID}"),
    ("PATCH", f"/api/v1/personas/{ID}"),
    ("DELETE", f"/api/v1/personas/{ID}"),
    ("GET", f"/api/v1/personas/{ID}/consentimiento"),
    ("POST", f"/api/v1/personas/{ID}/consentimiento"),
    ("DELETE", f"/api/v1/personas/{ID}/consentimiento"),
    ("GET", f"/api/v1/personas/{ID}/consentimientos"),
    ("GET", "/api/v1/consentimiento/texto"),
    ("GET", "/api/v1/horarios"),
    ("POST", "/api/v1/horarios"),
    ("PATCH", f"/api/v1/horarios/{ID}"),
    ("DELETE", f"/api/v1/horarios/{ID}"),
    ("GET", "/api/v1/dispositivos"),
    ("POST", "/api/v1/dispositivos"),
    ("GET", "/api/v1/dispositivos/entrada"),
    ("PATCH", "/api/v1/dispositivos/entrada"),
    ("POST", "/api/v1/dispositivos/entrada/token"),
]


def entrar(cliente: TestClient, correo: str, clave: str):
    return cliente.post("/api/v1/sesion", json={"correo": correo, "clave": clave})


# --- contrato API · iniciarSesion, verSesion y cerrarSesion ---


@pytest.mark.marca("contrato API · iniciarSesion")
def test_iniciar_sesion_devuelve_el_administrador(cliente: TestClient, administrador: dict) -> None:
    respuesta = entrar(cliente, administrador["correo"].upper(), administrador["clave"])

    assert respuesta.status_code == 200, respuesta.text
    validar("Administrador", respuesta.json())
    assert respuesta.json() == {
        "id": str(administrador["id"]),
        "correo": administrador["correo"],
        "nombre": administrador["nombre"],
    }


@pytest.mark.marca("contrato API · iniciarSesion")
@pytest.mark.parametrize("caso", ["clave equivocada", "correo que no existe", "administrador inactivo"])
def test_credenciales_que_no_sirven_dan_401_sin_decir_por_que(
    cliente: TestClient, administrador: dict, conexion: Connection, caso: str
) -> None:
    correo, clave = administrador["correo"], administrador["clave"]
    if caso == "clave equivocada":
        clave = "otra-clave-cualquiera"
    elif caso == "correo que no existe":
        correo = "nadie@example.com"
    else:
        conexion.execute(text("UPDATE administrador SET activo = false WHERE id = :id"), {"id": administrador["id"]})

    respuesta = entrar(cliente, correo, clave)

    assert respuesta.status_code == 401
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "credenciales_invalidas"
    assert "set-cookie" not in respuesta.headers


@pytest.mark.marca("contrato API · iniciarSesion")
@pytest.mark.parametrize("cuerpo", [{"correo": "admin@accesia.local", "clave": "clave-larga-1"}, {"correo": "admin@example.com", "clave": "corta"}, {}])
def test_credenciales_mal_formadas_dan_422(cliente: TestClient, cuerpo: dict) -> None:
    respuesta = cliente.post("/api/v1/sesion", json=cuerpo)

    assert respuesta.status_code == 422
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "validacion"


@pytest.mark.marca("contrato API · verSesion")
def test_ver_sesion_devuelve_el_administrador_y_renueva_la_cookie(sesion: TestClient, administrador: dict) -> None:
    respuesta = sesion.get("/api/v1/sesion")

    assert respuesta.status_code == 200
    validar("Administrador", respuesta.json())
    assert respuesta.json()["correo"] == administrador["correo"]
    # 8 horas desde el último uso: cada respuesta con sesión vuelve a dejar la cookie.
    assert f"{COOKIE}=" in respuesta.headers["set-cookie"]


@pytest.mark.marca("contrato API · cerrarSesion")
def test_cerrar_sesion_borra_la_cookie(sesion: TestClient) -> None:
    respuesta = sesion.delete("/api/v1/sesion")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    cookie = respuesta.headers["set-cookie"].lower()
    assert f"{COOKIE}=" in cookie and "max-age=0" in cookie
    assert sesion.get("/api/v1/sesion").status_code == 401


@pytest.mark.marca("contrato API · cerrarSesion")
def test_cerrar_sesion_sin_sesion_tambien_responde_204(cliente: TestClient) -> None:
    assert cliente.delete("/api/v1/sesion").status_code == 204


# --- RNF-02 · C2: cookie HttpOnly y SameSite=Strict; claves con Argon2 ---


@pytest.mark.marca("RNF-02 · C2")
def test_la_cookie_es_httponly_samesite_strict_y_de_ocho_horas(cliente: TestClient, administrador: dict) -> None:
    respuesta = entrar(cliente, administrador["correo"], administrador["clave"])

    cookie = respuesta.headers["set-cookie"].lower()
    assert cookie.startswith(f"{COOKIE}=")
    for atributo in ("httponly", "samesite=strict", "path=/", f"max-age={DURACION_S}"):
        assert atributo in cookie, f"Falta «{atributo}» en la cookie de sesión."
    assert "secure" not in cookie, "La red de la demo es HTTP: con Secure el navegador no enviaría la cookie."


@pytest.mark.marca("RNF-02 · C2")
def test_el_primer_administrador_se_crea_con_argon2id(conexion: Connection) -> None:
    assert crear_primer_administrador(conexion, "Primero@Example.com", "clave-inicial-123") is True

    fila = conexion.execute(
        text("SELECT correo, nombre, clave_hash, activo FROM administrador WHERE correo = 'primero@example.com'")
    ).one()
    assert fila.nombre == "Administrador"
    assert fila.activo is True
    assert fila.clave_hash.startswith("$argon2id$")
    assert "clave-inicial-123" not in fila.clave_hash


@pytest.mark.marca("RNF-02 · C2")
def test_si_el_primer_administrador_ya_existe_no_se_toca_su_clave(conexion: Connection) -> None:
    crear_primer_administrador(conexion, "primero@example.com", "clave-inicial-123")
    antes = conexion.execute(text("SELECT clave_hash FROM administrador WHERE correo = 'primero@example.com'")).scalar_one()

    assert crear_primer_administrador(conexion, "PRIMERO@example.com", "otra-clave-456") is False

    despues = conexion.execute(text("SELECT clave_hash FROM administrador WHERE correo = 'primero@example.com'")).scalar_one()
    assert despues == antes


@pytest.mark.marca("RNF-02 · C2")
@pytest.mark.parametrize(
    ("correo", "clave"),
    [(None, "clave-inicial-123"), ("primero@example.com", None), ("admin@accesia.local", "clave-inicial-123"), ("primero@example.com", "corta")],
)
def test_sin_datos_validos_no_se_crea_el_primer_administrador(conexion: Connection, correo, clave) -> None:
    antes = conexion.execute(text("SELECT count(*) FROM administrador")).scalar_one()

    assert crear_primer_administrador(conexion, correo, clave) is False

    assert conexion.execute(text("SELECT count(*) FROM administrador")).scalar_one() == antes


@pytest.mark.marca("RNF-02 · C2")
def test_el_arranque_crea_el_primer_administrador_de_infra_env(
    url_base: str, motor: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    correo = "arranque@example.com"
    monkeypatch.setenv("ADMIN_CORREO", correo)
    monkeypatch.setenv("ADMIN_CLAVE_INICIAL", "clave-de-arranque-123")
    configuracion.cache_clear()
    try:
        preparar_arranque()
        with motor.connect() as conexion:
            assert conexion.execute(text("SELECT count(*) FROM administrador WHERE correo = :c"), {"c": correo}).scalar_one() == 1
    finally:
        monkeypatch.undo()
        configuracion.cache_clear()
        with motor.begin() as conexion:
            conexion.execute(text("DELETE FROM administrador WHERE correo = :c"), {"c": correo})


@pytest.mark.marca("RNF-02 · C2")
def test_sin_sesion_secreto_el_servidor_no_arranca(url_base: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESION_SECRETO", "")
    configuracion.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="SESION_SECRETO"):
            preparar_arranque()
    finally:
        monkeypatch.undo()
        configuracion.cache_clear()


# --- RNF-02 · C5: sin sesión, 401 ---


@pytest.mark.marca("RNF-02 · C5")
@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_CON_SESION)
def test_sin_sesion_cada_ruta_responde_401(cliente: TestClient, metodo: str, ruta: str) -> None:
    respuesta = cliente.request(metodo, ruta, json={} if metodo in {"POST", "PATCH"} else None)

    assert respuesta.status_code == 401, f"{metodo} {ruta} respondió {respuesta.status_code}"
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "sin_sesion"


@pytest.mark.marca("RNF-02 · C5")
def test_una_cookie_con_firma_falsa_no_sirve(cliente: TestClient, administrador: dict) -> None:
    falsa = URLSafeTimedSerializer("otro-secreto", salt=SAL).dumps(str(administrador["id"]))
    cliente.cookies.set(COOKIE, falsa)

    assert cliente.get("/api/v1/sesion").status_code == 401


@pytest.mark.marca("RNF-02 · C5")
def test_una_cookie_de_hace_mas_de_ocho_horas_ya_vencio(cliente: TestClient, administrador: dict) -> None:
    class FirmadorDeHaceNueveHoras(TimestampSigner):
        def get_timestamp(self) -> int:
            return int(time.time()) - 9 * 60 * 60

    secreto = configuracion().sesion_secreto.get_secret_value()
    vieja = URLSafeTimedSerializer(secreto, salt=SAL, signer=FirmadorDeHaceNueveHoras).dumps(str(administrador["id"]))
    cliente.cookies.set(COOKIE, vieja)

    assert cliente.get("/api/v1/sesion").status_code == 401


@pytest.mark.marca("RNF-02 · C5")
def test_un_administrador_desactivado_pierde_la_sesion(sesion: TestClient, administrador: dict, conexion: Connection) -> None:
    conexion.execute(text("UPDATE administrador SET activo = false WHERE id = :id"), {"id": administrador["id"]})

    respuesta = sesion.get("/api/v1/sesion")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "sin_sesion"
