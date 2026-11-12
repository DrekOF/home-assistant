"""
Nombre: test_horarios.py
Descripción: Pruebas de los horarios por bloques (D-20): contrato de sus operaciones y RF-13 · C1 a C3.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from uuid import uuid4

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection

HORARIOS = "/api/v1/horarios"
LUNES_Y_MIERCOLES = [
    {"dia": 3, "hora_inicio": "18:00", "tolerancia_min": 15},
    {"dia": 1, "hora_inicio": "07:00", "tolerancia_min": 10},
]


def crear(sesion: TestClient, nombre: str = "Lunes y miércoles", bloques: list | None = None) -> dict:
    respuesta = sesion.post(HORARIOS, json={"nombre": nombre, "bloques": bloques or LUNES_Y_MIERCOLES})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


# --- contrato API · listarHorarios, crearHorario, editarHorario y borrarHorario ---


@pytest.mark.marca("contrato API · listarHorarios")
def test_listar_trae_el_horario_de_ejemplo_con_sus_bloques(sesion: TestClient) -> None:
    respuesta = sesion.get(HORARIOS)

    assert respuesta.status_code == 200
    horarios = respuesta.json()
    for horario in horarios:
        validar("Horario", horario)
    clase_ia = next(h for h in horarios if h["nombre"] == "Clase IA")
    assert clase_ia["bloques"] == [{"dia": dia, "hora_inicio": "07:00", "tolerancia_min": 10} for dia in range(1, 6)]


@pytest.mark.marca("contrato API · crearHorario")
@pytest.mark.parametrize(
    "bloques",
    [
        [],
        [{"dia": 1, "hora_inicio": "07:00", "tolerancia_min": 10}] * 8,
        [{"dia": 0, "hora_inicio": "07:00", "tolerancia_min": 10}],
        [{"dia": 1, "hora_inicio": "7:00", "tolerancia_min": 10}],
        [{"dia": 1, "hora_inicio": "24:00", "tolerancia_min": 10}],
        [{"dia": 1, "hora_inicio": "07:00", "tolerancia_min": 121}],
        [{"dia": 1, "hora_inicio": "07:00"}],
    ],
)
def test_crear_con_bloques_que_no_sirven_da_422(sesion: TestClient, bloques: list) -> None:
    error(sesion.post(HORARIOS, json={"nombre": "Horario raro", "bloques": bloques}), 422, "validacion")


@pytest.mark.marca("contrato API · editarHorario")
def test_editar_un_horario_que_no_existe_da_404_y_sin_cambios_422(sesion: TestClient) -> None:
    horario = crear(sesion)

    error(sesion.patch(f"{HORARIOS}/{uuid4()}", json={"nombre": "Otro"}), 404, "no_encontrado")
    error(sesion.patch(f"{HORARIOS}/{horario['id']}", json={}), 422, "validacion")
    error(sesion.patch(f"{HORARIOS}/{horario['id']}", json={"bloques": None}), 422, "validacion")


@pytest.mark.marca("contrato API · borrarHorario")
def test_borrar_un_horario_que_no_existe_da_404(sesion: TestClient) -> None:
    error(sesion.delete(f"{HORARIOS}/{uuid4()}"), 404, "no_encontrado")
    error(sesion.delete(f"{HORARIOS}/no-es-un-uuid"), 404, "no_encontrado")


# --- RF-13 · C1: crear con bloques, uno por día ---


@pytest.mark.marca("RF-13 · C1")
def test_crear_un_horario_con_bloques_ordenados_por_dia(sesion: TestClient) -> None:
    horario = crear(sesion)

    validar("Horario", horario)
    assert horario["nombre"] == "Lunes y miércoles"
    assert [b["dia"] for b in horario["bloques"]] == [1, 3]
    assert horario["bloques"][1] == {"dia": 3, "hora_inicio": "18:00", "tolerancia_min": 15}


@pytest.mark.marca("RF-13 · C1")
def test_un_dia_repetido_da_422(sesion: TestClient) -> None:
    bloques = [{"dia": 2, "hora_inicio": "07:00", "tolerancia_min": 10}, {"dia": 2, "hora_inicio": "18:00", "tolerancia_min": 10}]

    respuesta = sesion.post(HORARIOS, json={"nombre": "Martes dos veces", "bloques": bloques})

    error(respuesta, 422, "validacion")
    assert "un solo bloque" in respuesta.json()["detalle"]


@pytest.mark.marca("RF-13 · C1")
def test_un_nombre_repetido_da_409_y_la_prueba_sigue(sesion: TestClient) -> None:
    otro = crear(sesion, nombre="Sábados", bloques=[{"dia": 6, "hora_inicio": "08:00", "tolerancia_min": 15}])

    error(sesion.post(HORARIOS, json={"nombre": "Clase IA", "bloques": LUNES_Y_MIERCOLES}), 409, "nombre_duplicado")
    error(sesion.patch(f"{HORARIOS}/{otro['id']}", json={"nombre": "Clase IA"}), 409, "nombre_duplicado")

    nombres = [h["nombre"] for h in sesion.get(HORARIOS).json()]
    assert nombres.count("Clase IA") == 1 and "Sábados" in nombres


# --- RF-13 · C2: editar los bloques reemplaza la lista completa ---


@pytest.mark.marca("RF-13 · C2")
def test_editar_los_bloques_reemplaza_la_lista(sesion: TestClient) -> None:
    horario = crear(sesion)

    respuesta = sesion.patch(
        f"{HORARIOS}/{horario['id']}", json={"bloques": [{"dia": 5, "hora_inicio": "06:30", "tolerancia_min": 5}]}
    )

    assert respuesta.status_code == 200, respuesta.text
    validar("Horario", respuesta.json())
    assert respuesta.json()["bloques"] == [{"dia": 5, "hora_inicio": "06:30", "tolerancia_min": 5}]


@pytest.mark.marca("RF-13 · C2")
def test_cambiar_solo_el_nombre_conserva_los_bloques(sesion: TestClient) -> None:
    horario = crear(sesion)

    respuesta = sesion.patch(f"{HORARIOS}/{horario['id']}", json={"nombre": "Clase de lunes y miércoles"})

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Clase de lunes y miércoles"
    assert respuesta.json()["bloques"] == horario["bloques"]


# --- RF-13 · C3: un horario en uso no se borra ---


@pytest.mark.marca("RF-13 · C3")
def test_un_horario_en_uso_no_se_borra(sesion: TestClient, conexion: Connection) -> None:
    horario = crear(sesion)
    persona_id = armar.persona(conexion, horario_id=horario["id"])

    error(sesion.delete(f"{HORARIOS}/{horario['id']}"), 409, "horario_en_uso")

    # El error corrió en su savepoint: la prueba sigue, el horario sigue y, sin la persona, ya se borra.
    assert any(h["id"] == horario["id"] for h in sesion.get(HORARIOS).json())
    assert sesion.patch(f"/api/v1/personas/{persona_id}", json={"horario_id": None}).status_code == 200
    assert sesion.delete(f"{HORARIOS}/{horario['id']}").status_code == 204
    assert all(h["id"] != horario["id"] for h in sesion.get(HORARIOS).json())
