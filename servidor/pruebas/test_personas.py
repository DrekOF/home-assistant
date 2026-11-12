"""
Nombre: test_personas.py
Descripción: Pruebas de la API de personas: contrato de sus cinco operaciones, RF-02 · C1, RF-12 · C2, R8 · formato y R9 · desactivar no cancela.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import re
from datetime import timedelta
from uuid import uuid4

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from accesia.tiempo import ahora

PERSONAS = "/api/v1/personas"


def crear(sesion: TestClient, **campos) -> dict:
    datos = {"documento": "1075000001", "nombre": "Ana María Gómez Rojas", **campos}
    respuesta = sesion.post(PERSONAS, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def clase_ia(conexion: Connection) -> str:
    return str(conexion.execute(text("SELECT id FROM horario WHERE nombre = 'Clase IA'")).scalar_one())


def error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


# --- contrato API · crearPersona, verPersona, editarPersona, borrarPersona y listarPersonas ---


@pytest.mark.marca("contrato API · crearPersona")
def test_crear_una_persona_con_los_valores_por_defecto(sesion: TestClient) -> None:
    persona = crear(sesion, nombre="  Ana María Gómez Rojas  ")

    validar("Persona", persona)
    assert persona["nombre"] == "Ana María Gómez Rojas"
    assert persona["rol"] == "estudiante"
    assert persona["activa"] is True
    assert persona["horario_id"] is None and persona["horario_nombre"] is None
    assert persona["consentimiento_vigente"] is False
    assert persona["muestras"] == 0


@pytest.mark.marca("contrato API · crearPersona")
def test_crear_una_persona_con_horario(sesion: TestClient, conexion: Connection) -> None:
    persona = crear(sesion, rol="docente", horario_id=clase_ia(conexion))

    assert persona["rol"] == "docente"
    assert persona["horario_nombre"] == "Clase IA"


@pytest.mark.marca("contrato API · crearPersona")
@pytest.mark.parametrize(
    "campos",
    [
        {"documento": "10 75"},
        {"documento": "12"},
        {"nombre": " A "},
        {"rol": "visitante"},
        {"horario_id": str(uuid4())},
        {"activa": None},
    ],
)
def test_crear_una_persona_con_datos_que_no_sirven_da_422(sesion: TestClient, campos: dict) -> None:
    respuesta = sesion.post(PERSONAS, json={"documento": "1075000001", "nombre": "Ana María Gómez", **campos})

    error(respuesta, 422, "validacion")


@pytest.mark.marca("contrato API · verPersona")
def test_ver_una_persona(sesion: TestClient) -> None:
    creada = crear(sesion)

    respuesta = sesion.get(f"{PERSONAS}/{creada['id']}")

    assert respuesta.status_code == 200
    validar("Persona", respuesta.json())
    assert respuesta.json() == creada


@pytest.mark.marca("contrato API · verPersona")
@pytest.mark.parametrize("persona_id", [str(uuid4()), "no-es-un-uuid"])
def test_ver_una_persona_que_no_existe_da_404(sesion: TestClient, persona_id: str) -> None:
    error(sesion.get(f"{PERSONAS}/{persona_id}"), 404, "no_encontrado")


@pytest.mark.marca("contrato API · editarPersona")
def test_editar_una_persona(sesion: TestClient, conexion: Connection) -> None:
    creada = crear(sesion, horario_id=clase_ia(conexion))

    respuesta = sesion.patch(f"{PERSONAS}/{creada['id']}", json={"nombre": "Ana Gómez", "horario_id": None})

    assert respuesta.status_code == 200, respuesta.text
    persona = respuesta.json()
    validar("Persona", persona)
    assert persona["nombre"] == "Ana Gómez"
    assert persona["horario_id"] is None
    assert persona["documento"] == creada["documento"], "Lo que no llega en el PATCH no cambia."
    assert persona["actualizada"] >= creada["actualizada"]


@pytest.mark.marca("contrato API · editarPersona")
@pytest.mark.parametrize("cambios", [{}, {"nombre": None}, {"documento": "x"}, {"horario_id": str(uuid4())}])
def test_editar_con_datos_que_no_sirven_da_422(sesion: TestClient, cambios: dict) -> None:
    creada = crear(sesion)

    error(sesion.patch(f"{PERSONAS}/{creada['id']}", json=cambios), 422, "validacion")


@pytest.mark.marca("contrato API · editarPersona")
def test_editar_una_persona_que_no_existe_da_404(sesion: TestClient) -> None:
    error(sesion.patch(f"{PERSONAS}/{uuid4()}", json={"nombre": "Nadie"}), 404, "no_encontrado")


@pytest.mark.marca("contrato API · borrarPersona")
def test_borrar_una_persona(sesion: TestClient) -> None:
    creada = crear(sesion)

    respuesta = sesion.delete(f"{PERSONAS}/{creada['id']}")

    assert respuesta.status_code == 204
    error(sesion.get(f"{PERSONAS}/{creada['id']}"), 404, "no_encontrado")
    error(sesion.delete(f"{PERSONAS}/{creada['id']}"), 404, "no_encontrado")


@pytest.mark.marca("contrato API · listarPersonas")
def test_listar_pagina_y_ordena_por_nombre_en_espanol(sesion: TestClient) -> None:
    for documento, nombre in [("1001", "Óscar Peña"), ("1002", "Ñusta Quispe"), ("1003", "Nora Díaz"), ("1004", "ana lópez")]:
        crear(sesion, documento=documento, nombre=nombre)

    primera = sesion.get(PERSONAS, params={"por_pagina": 3}).json()
    segunda = sesion.get(PERSONAS, params={"por_pagina": 3, "pagina": 2}).json()

    validar("PaginaPersonas", primera)
    assert (primera["total"], primera["pagina"], primera["por_pagina"]) == (4, 1, 3)
    nombres = [p["nombre"] for p in primera["elementos"] + segunda["elementos"]]
    assert nombres == ["ana lópez", "Nora Díaz", "Ñusta Quispe", "Óscar Peña"]


@pytest.mark.marca("contrato API · listarPersonas")
@pytest.mark.parametrize(
    ("q", "esperados"),
    [("gomez", ["Ana María Gómez Rojas"]), ("ANA", ["Ana María Gómez Rojas"]), ("2002", ["Bruno Peña"]), ("%", []), ("a_m", [])],
)
def test_buscar_sin_importar_tildes_ni_mayusculas(sesion: TestClient, q: str, esperados: list[str]) -> None:
    crear(sesion, documento="1075000001", nombre="Ana María Gómez Rojas")
    crear(sesion, documento="2002", nombre="Bruno Peña")

    respuesta = sesion.get(PERSONAS, params={"q": q})

    assert respuesta.status_code == 200
    assert [p["nombre"] for p in respuesta.json()["elementos"]] == esperados


@pytest.mark.marca("contrato API · listarPersonas")
@pytest.mark.parametrize("parametros", [{"q": "x" * 61}, {"pagina": 0}, {"por_pagina": 101}, {"activa": "quizas"}])
def test_listar_con_parametros_que_no_sirven_da_422(sesion: TestClient, parametros: dict) -> None:
    error(sesion.get(PERSONAS, params=parametros), 422, "validacion")


# --- RF-02 · C1: documento único, activar y desactivar ---


@pytest.mark.marca("RF-02 · C1")
def test_el_documento_es_unico_y_la_prueba_sigue_despues_del_409(sesion: TestClient) -> None:
    primera = crear(sesion, documento="1075000001")
    otra = crear(sesion, documento="1075000002", nombre="Bruno Peña")

    error(sesion.post(PERSONAS, json={"documento": "1075000001", "nombre": "Otra Persona"}), 409, "documento_duplicado")
    error(sesion.patch(f"{PERSONAS}/{otra['id']}", json={"documento": "1075000001"}), 409, "documento_duplicado")

    # El error corrió en su savepoint: la transacción sigue sana y nada cambió.
    listado = sesion.get(PERSONAS).json()
    assert listado["total"] == 2
    assert sesion.get(f"{PERSONAS}/{otra['id']}").json()["documento"] == "1075000002"
    assert primera["documento"] == "1075000001"


@pytest.mark.marca("RF-02 · C1")
def test_activar_y_desactivar_una_persona(sesion: TestClient) -> None:
    creada = crear(sesion)

    desactivada = sesion.patch(f"{PERSONAS}/{creada['id']}", json={"activa": False}).json()
    inactivas = sesion.get(PERSONAS, params={"activa": False}).json()
    activas = sesion.get(PERSONAS, params={"activa": True}).json()
    activada = sesion.patch(f"{PERSONAS}/{creada['id']}", json={"activa": True}).json()

    assert desactivada["activa"] is False
    assert [p["id"] for p in inactivas["elementos"]] == [creada["id"]]
    assert activas["total"] == 0
    assert activada["activa"] is True


# --- RF-12 · C2: borrar una persona y lo suyo ---


@pytest.mark.marca("RF-12 · C2")
def test_borrar_una_persona_borra_lo_suyo_y_deja_sus_eventos_sin_persona(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)
    camara = armar.camara(conexion)
    armar.consentimiento(conexion, persona_id)
    inscripcion_id = armar.inscripcion(conexion, persona_id, camara, ahora() + timedelta(seconds=60))
    armar.rostro(conexion, persona_id, inscripcion_id)
    armar.asistencia(conexion, persona_id)
    evento_id = armar.evento(conexion, camara, persona_id)

    assert sesion.delete(f"{PERSONAS}/{persona_id}").status_code == 204

    for tabla in ("consentimiento", "inscripcion", "rostro", "asistencia"):
        assert armar.contar(conexion, tabla, persona_id) == 0, f"Quedó algo en {tabla}."
    evento = conexion.execute(text("SELECT persona_id FROM evento_acceso WHERE id = :id"), {"id": evento_id}).one()
    assert evento.persona_id is None


# --- R8 · formato ---


@pytest.mark.marca("R8 · formato")
def test_las_fechas_salen_en_iso_8601_con_la_zona_de_colombia(sesion: TestClient) -> None:
    persona = crear(sesion)

    for campo in ("creada", "actualizada"):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-05:00", persona[campo]), persona[campo]


# --- R9 · desactivar no cancela ---


@pytest.mark.marca("R9 · desactivar no cancela")
def test_desactivar_a_la_persona_no_cancela_su_inscripcion(sesion: TestClient, conexion: Connection) -> None:
    persona_id = armar.persona(conexion)
    armar.consentimiento(conexion, persona_id)
    inscripcion_id = armar.inscripcion(conexion, persona_id, armar.camara(conexion), ahora() + timedelta(seconds=60), muestras=2)

    assert sesion.patch(f"{PERSONAS}/{persona_id}", json={"activa": False}).status_code == 200

    estado = conexion.execute(text("SELECT estado FROM inscripcion WHERE id = :id"), {"id": inscripcion_id}).scalar_one()
    assert estado == "activa"
