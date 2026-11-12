"""
Nombre: test_camaras.py
Descripción: Pruebas de la API de cámaras: contrato de sus operaciones, inscripcion_activa (contrato 1.3) y RF-10 · C1 a C3.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import hashlib
from datetime import timedelta

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from accesia.tiempo import ahora

DISPOSITIVOS = "/api/v1/dispositivos"


def crear(sesion: TestClient, codigo: str = "entrada", **campos) -> dict:
    datos = {"codigo": codigo, "nombre": "Entrada", "tipo": "simulador", **campos}
    respuesta = sesion.post(DISPOSITIVOS, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def hash_guardado(conexion: Connection, codigo: str) -> str:
    return conexion.execute(text("SELECT token_hash FROM dispositivo WHERE codigo = :c"), {"c": codigo}).scalar_one()


def sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


# --- contrato API · crearCamara, verCamara, editarCamara, listarCamaras y cambiarTokenCamara ---


@pytest.mark.marca("contrato API · crearCamara")
@pytest.mark.parametrize(
    "campos",
    [
        {"codigo": "servidor"},
        {"codigo": "Entrada"},
        {"codigo": "ab"},
        {"nombre": "E"},
        {"tipo": "webcam"},
        {"tipo": "respaldo"},
        {"tipo": "respaldo", "url_captura": "no es una url"},
    ],
)
def test_crear_con_datos_que_no_sirven_da_422(sesion: TestClient, campos: dict) -> None:
    datos = {"codigo": "entrada", "nombre": "Entrada", "tipo": "simulador", **campos}

    error(sesion.post(DISPOSITIVOS, json=datos), 422, "validacion")


@pytest.mark.marca("contrato API · crearCamara")
def test_el_codigo_servidor_esta_reservado(sesion: TestClient) -> None:
    respuesta = sesion.post(DISPOSITIVOS, json={"codigo": "servidor", "nombre": "Servidor", "tipo": "simulador"})

    error(respuesta, 422, "validacion")
    assert "reservado" in respuesta.json()["detalle"]


@pytest.mark.marca("contrato API · crearCamara")
def test_un_codigo_repetido_da_409(sesion: TestClient) -> None:
    crear(sesion)

    error(sesion.post(DISPOSITIVOS, json={"codigo": "entrada", "nombre": "Otra", "tipo": "tinyml"}), 409, "codigo_duplicado")
    assert len(sesion.get(DISPOSITIVOS).json()) == 1


@pytest.mark.marca("contrato API · crearCamara")
def test_una_camara_de_respaldo_con_su_url(sesion: TestClient) -> None:
    camara = crear(sesion, codigo="respaldo-1", tipo="respaldo", url_captura="http://10.42.0.30/capture")

    assert camara["tipo"] == "respaldo"
    assert camara["url_captura"] == "http://10.42.0.30/capture"


@pytest.mark.marca("contrato API · verCamara")
def test_ver_una_camara_que_no_existe_da_404(sesion: TestClient) -> None:
    error(sesion.get(f"{DISPOSITIVOS}/no-existe"), 404, "no_encontrado")


@pytest.mark.marca("contrato API · editarCamara")
def test_editar_una_camara(sesion: TestClient) -> None:
    crear(sesion)

    respuesta = sesion.patch(f"{DISPOSITIVOS}/entrada", json={"nombre": "Puerta principal", "activo": False})

    assert respuesta.status_code == 200, respuesta.text
    validar("Dispositivo", respuesta.json())
    assert respuesta.json()["nombre"] == "Puerta principal"
    assert respuesta.json()["activo"] is False
    assert "token" not in respuesta.json()


@pytest.mark.marca("contrato API · editarCamara")
@pytest.mark.parametrize("cambios", [{}, {"tipo": "respaldo"}, {"nombre": None}, {"activo": None}])
def test_editar_con_datos_que_no_sirven_da_422(sesion: TestClient, cambios: dict) -> None:
    crear(sesion)

    error(sesion.patch(f"{DISPOSITIVOS}/entrada", json=cambios), 422, "validacion")


@pytest.mark.marca("contrato API · editarCamara")
def test_a_una_camara_de_respaldo_no_se_le_quita_la_url(sesion: TestClient) -> None:
    crear(sesion, codigo="respaldo-1", tipo="respaldo", url_captura="http://10.42.0.30/capture")

    error(sesion.patch(f"{DISPOSITIVOS}/respaldo-1", json={"url_captura": None}), 422, "validacion")
    error(sesion.patch(f"{DISPOSITIVOS}/no-existe", json={"nombre": "Nadie"}), 404, "no_encontrado")


@pytest.mark.marca("contrato API · listarCamaras")
def test_listar_ordena_por_codigo(sesion: TestClient) -> None:
    for codigo in ("salida", "entrada", "patio"):
        crear(sesion, codigo=codigo)

    respuesta = sesion.get(DISPOSITIVOS)

    assert respuesta.status_code == 200
    for camara in respuesta.json():
        validar("Dispositivo", camara)
        assert "token" not in camara
    assert [c["codigo"] for c in respuesta.json()] == ["entrada", "patio", "salida"]


@pytest.mark.marca("contrato API · cambiarTokenCamara")
def test_cambiar_el_token_de_una_camara_que_no_existe_da_404(sesion: TestClient) -> None:
    error(sesion.post(f"{DISPOSITIVOS}/no-existe/token"), 404, "no_encontrado")


@pytest.mark.marca("contrato API · inscripcion_activa")
def test_la_camara_muestra_su_inscripcion_activa_y_vence_la_pasada(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)
    vence = ahora() + timedelta(seconds=90)
    activa = armar.inscripcion(conexion, persona_id, armar.camara(conexion, "entrada"), vence, muestras=3)
    pasada_vence = ahora() - timedelta(seconds=10)
    pasada = armar.inscripcion(conexion, persona_id, armar.camara(conexion, "salida"), pasada_vence, muestras=2)

    entrada = sesion.get(f"{DISPOSITIVOS}/entrada").json()
    camaras = {c["codigo"]: c for c in sesion.get(DISPOSITIVOS).json()}

    validar("Dispositivo", entrada)
    assert entrada["modo"] == "inscribir"
    assert entrada["inscripcion_activa"] == {
        "id": str(activa),
        "muestras": 3,
        "requeridas": 5,
        "estado": "activa",
        "vence": vence.isoformat(),
    }
    assert camaras["entrada"] == entrada
    assert camaras["salida"]["modo"] == "reconocer"
    assert camaras["salida"]["inscripcion_activa"] is None
    fila = conexion.execute(text("SELECT estado, terminada, vence FROM inscripcion WHERE id = :id"), {"id": pasada}).one()
    assert fila.estado == "vencida"
    assert fila.terminada == fila.vence, "Una inscripción vencida termina a la hora en que venció (R9)."


# --- RF-10 · C1: el token se muestra una sola vez y se guarda como hash ---


@pytest.mark.marca("RF-10 · C1")
def test_crear_una_camara_muestra_el_token_una_vez_y_guarda_su_hash(sesion: TestClient, conexion: Connection) -> None:
    camara = crear(sesion)

    validar("DispositivoConToken", camara)
    assert len(camara["token"]) >= 43, "El token sale de 32 bytes aleatorios."
    assert hash_guardado(conexion, "entrada") == sha256(camara["token"])
    assert camara["token"] not in hash_guardado(conexion, "entrada")
    assert (camara["modo"], camara["inscripcion_activa"], camara["en_linea"], camara["estado"]) == ("reconocer", None, False, None)
    vista = sesion.get(f"{DISPOSITIVOS}/entrada").json()
    validar("Dispositivo", vista)
    assert "token" not in vista


# --- RF-10 · C2: cambiar el token ---


@pytest.mark.marca("RF-10 · C2")
def test_cambiar_el_token_deja_sin_servir_el_anterior(sesion: TestClient, conexion: Connection) -> None:
    anterior = crear(sesion)["token"]

    respuesta = sesion.post(f"{DISPOSITIVOS}/entrada/token")

    assert respuesta.status_code == 200, respuesta.text
    validar("DispositivoConToken", respuesta.json())
    nuevo = respuesta.json()["token"]
    assert nuevo != anterior
    assert hash_guardado(conexion, "entrada") == sha256(nuevo)
    assert hash_guardado(conexion, "entrada") != sha256(anterior)


# --- RF-10 · C3: último contacto y en línea ---


@pytest.mark.marca("RF-10 · C3")
@pytest.mark.parametrize(("hace", "en_linea"), [(timedelta(seconds=30), True), (timedelta(minutes=5), False), (None, False)])
def test_en_linea_si_hizo_contacto_en_los_ultimos_dos_minutos(
    sesion: TestClient, conexion: Connection, hace: timedelta | None, en_linea: bool
) -> None:
    contacto = None if hace is None else ahora() - hace
    armar.camara(conexion, "entrada", ultimo_contacto=contacto)

    camara = sesion.get(f"{DISPOSITIVOS}/entrada").json()

    assert camara["en_linea"] is en_linea
    assert camara["ultimo_contacto"] == (None if contacto is None else contacto.isoformat())
