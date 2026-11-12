"""
Nombre: test_consentimiento.py
Descripción: Pruebas del consentimiento: contrato de sus operaciones, RF-02 · C2, RF-02 · C3, RF-02 · C5 y R9 · revoca a mitad.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from datetime import datetime, timedelta
from uuid import uuid4

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from accesia.consentimiento import ruta_del_texto
from accesia.tiempo import ahora

PERSONAS = "/api/v1/personas"


def ruta(persona_id) -> str:
    return f"{PERSONAS}/{persona_id}/consentimiento"


def registrar(sesion: TestClient, persona_id, **campos):
    return sesion.post(ruta(persona_id), json={"version_texto": "1.0", "acepta": True, **campos})


def error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


# --- contrato API · verTextoConsentimiento (RF-02 · C3) ---


@pytest.mark.marca("contrato API · verTextoConsentimiento")
def test_el_texto_sale_de_consentimiento_md(sesion: TestClient) -> None:
    respuesta = sesion.get("/api/v1/consentimiento/texto")

    assert respuesta.status_code == 200
    validar("TextoConsentimiento", respuesta.json())
    texto = respuesta.json()["texto"]
    assert respuesta.json()["version"] == "1.0"
    assert texto.startswith("**Autorización para el tratamiento de mis datos biométricos")
    assert "**No es obligatorio.**" in texto
    assert "---" not in texto and "Referencias" not in texto, "Solo va el bloque entre las dos líneas ---."
    assert texto in ruta_del_texto().read_text(encoding="utf-8")


# --- contrato API · verConsentimiento, registrarConsentimiento, revocarConsentimiento y listarConsentimientos ---


@pytest.mark.marca("contrato API · verConsentimiento")
def test_sin_consentimiento_vigente_responde_null(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)

    respuesta = sesion.get(ruta(persona_id))

    assert respuesta.status_code == 200
    assert respuesta.json() is None


@pytest.mark.marca("contrato API · verConsentimiento")
def test_ver_el_consentimiento_de_una_persona_que_no_existe_da_404(sesion: TestClient) -> None:
    error(sesion.get(ruta(uuid4())), 404, "no_encontrado")


@pytest.mark.marca("contrato API · registrarConsentimiento")
@pytest.mark.parametrize(
    ("campos", "estado", "codigo"),
    [
        ({"version_texto": "0.9"}, 422, "version_texto_invalida"),
        ({"acepta": False}, 422, "validacion"),
        ({"medio": "fax"}, 422, "validacion"),
        ({"medio": "papel", "aceptado_en": "2026-11-10T08:00:00"}, 422, "validacion"),
    ],
)
def test_registrar_con_datos_que_no_sirven(sesion: TestClient, conexion: Connection, campos, estado, codigo) -> None:
    persona_id = armar.persona(conexion)

    error(registrar(sesion, persona_id, **campos), estado, codigo)


@pytest.mark.marca("contrato API · registrarConsentimiento")
def test_registrar_dos_veces_da_409_y_a_alguien_que_no_existe_404(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)
    assert registrar(sesion, persona_id).status_code == 201

    error(registrar(sesion, persona_id), 409, "consentimiento_vigente")
    error(registrar(sesion, uuid4()), 404, "no_encontrado")
    assert sesion.get(ruta(persona_id)).json() is not None


@pytest.mark.marca("contrato API · revocarConsentimiento")
def test_revocar_sin_consentimiento_vigente_da_404(sesion: TestClient, conexion: Connection) -> None:
    error(sesion.delete(ruta(armar.persona(conexion))), 404, "no_encontrado")
    error(sesion.delete(ruta(uuid4())), 404, "no_encontrado")


@pytest.mark.marca("contrato API · listarConsentimientos")
def test_el_historial_va_del_mas_reciente_al_mas_antiguo(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)
    papel = registrar(sesion, persona_id, medio="papel", aceptado_en="2026-11-10T08:00:00-05:00").json()
    assert sesion.delete(ruta(persona_id)).status_code == 204
    web = registrar(sesion, persona_id).json()

    respuesta = sesion.get(f"{PERSONAS}/{persona_id}/consentimientos")

    assert respuesta.status_code == 200
    historial = respuesta.json()
    for consentimiento in historial:
        validar("Consentimiento", consentimiento)
    assert [c["id"] for c in historial] == [web["id"], papel["id"]]
    assert historial[0]["revocado_en"] is None
    assert historial[1]["revocado_en"] is not None
    error(sesion.get(f"{PERSONAS}/{uuid4()}/consentimientos"), 404, "no_encontrado")


# --- RF-02 · C2: versión del texto, medio, quién lo registró y fecha ---


@pytest.mark.marca("RF-02 · C2")
def test_registrar_por_la_web_guarda_version_medio_autor_y_fecha(
    sesion: TestClient, conexion: Connection, administrador: dict
) -> None:
    persona_id = armar.persona(conexion)
    antes = ahora()

    respuesta = registrar(sesion, persona_id)

    assert respuesta.status_code == 201, respuesta.text
    consentimiento = respuesta.json()
    validar("Consentimiento", consentimiento)
    assert consentimiento["version_texto"] == "1.0"
    assert consentimiento["medio"] == "web"
    assert consentimiento["registrado_por"] == administrador["nombre"]
    assert consentimiento["revocado_en"] is None
    assert datetime.fromisoformat(consentimiento["aceptado_en"]) >= antes
    assert sesion.get(ruta(persona_id)).json() == consentimiento
    assert sesion.get(f"{PERSONAS}/{persona_id}").json()["consentimiento_vigente"] is True
    guardado = conexion.execute(
        text("SELECT registrado_por FROM consentimiento WHERE id = :id"), {"id": consentimiento["id"]}
    ).scalar_one()
    assert guardado == administrador["id"]


@pytest.mark.marca("RF-02 · C2")
def test_registrar_en_papel_guarda_la_fecha_de_la_firma(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)

    respuesta = registrar(sesion, persona_id, medio="papel", aceptado_en="2026-11-10T08:00:00-05:00")

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["medio"] == "papel"
    assert respuesta.json()["aceptado_en"] == "2026-11-10T08:00:00-05:00"


@pytest.mark.marca("RF-02 · C2")
def test_la_fecha_de_la_firma_no_puede_ser_futura(sesion: TestClient, conexion: Connection) -> None:
    manana = (ahora() + timedelta(days=1)).isoformat()

    error(registrar(sesion, armar.persona(conexion), medio="papel", aceptado_en=manana), 422, "validacion")


@pytest.mark.marca("RF-02 · C2")
def test_con_medio_web_la_fecha_es_la_del_registro(sesion: TestClient, conexion: Connection) -> None:
    antes = ahora()

    respuesta = registrar(sesion, armar.persona(conexion), aceptado_en="2026-01-01T08:00:00-05:00")

    assert respuesta.status_code == 201
    assert datetime.fromisoformat(respuesta.json()["aceptado_en"]) >= antes


# --- RF-02 · C5 y R9 · revoca a mitad ---


@pytest.mark.marca("RF-02 · C5")
def test_revocar_borra_las_huellas(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)
    assert registrar(sesion, persona_id).status_code == 201
    armar.rostro(conexion, persona_id)
    armar.rostro(conexion, persona_id)
    assert sesion.get(f"{PERSONAS}/{persona_id}").json()["muestras"] == 2

    respuesta = sesion.delete(ruta(persona_id))

    assert respuesta.status_code == 204
    assert armar.contar(conexion, "rostro", persona_id) == 0
    assert sesion.get(ruta(persona_id)).json() is None
    persona = sesion.get(f"{PERSONAS}/{persona_id}").json()
    assert persona["muestras"] == 0 and persona["consentimiento_vigente"] is False


@pytest.mark.marca("R9 · revoca a mitad")
def test_revocar_a_mitad_de_la_inscripcion_la_cancela(sesion: TestClient, conexion: Connection) -> None:
    ana = armar.persona(conexion)
    bruno = armar.persona(conexion, documento="2002", nombre="Bruno Peña")
    assert registrar(sesion, ana).status_code == 201
    armar.consentimiento(conexion, bruno)
    vence = ahora() + timedelta(seconds=90)
    de_ana = armar.inscripcion(conexion, ana, armar.camara(conexion, "entrada"), vence, muestras=2)
    de_bruno = armar.inscripcion(conexion, bruno, armar.camara(conexion, "salida"), vence, muestras=1)
    for _ in range(2):
        armar.rostro(conexion, ana, de_ana)
    armar.rostro(conexion, bruno, de_bruno)

    assert sesion.delete(ruta(ana)).status_code == 204

    estado = dict(conexion.execute(text("SELECT id, estado FROM inscripcion")).all())
    assert estado[de_ana] == "cancelada"
    assert estado[de_bruno] == "activa", "Solo se cancela la inscripción de quien revoca."
    terminada = conexion.execute(text("SELECT terminada FROM inscripcion WHERE id = :id"), {"id": de_ana}).scalar_one()
    assert terminada is not None
    assert armar.contar(conexion, "rostro", ana) == 0
    assert armar.contar(conexion, "rostro", bruno) == 1
    assert sesion.get("/api/v1/dispositivos/entrada").json()["modo"] == "reconocer"
