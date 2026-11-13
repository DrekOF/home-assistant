"""
Nombre: test_huellas.py
Descripción: Pruebas de las huellas de una persona: RF-12 · C1 (borrar todas o una) y el contrato de listarRostros, borrarRostros y borrarRostro, que nunca devuelven la huella.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection

BOGOTA = ZoneInfo("America/Bogota")


def rostros_de(persona_id) -> str:
    return f"/api/v1/personas/{persona_id}/rostros"


def error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


# --- RF-12 · C1: borrar las huellas ---


@pytest.mark.marca("RF-12 · C1")
def test_borrar_todas_las_huellas_de_una_persona(sesion: TestClient, conexion: Connection) -> None:
    ana = armar.persona(conexion)
    bruno = armar.persona(conexion, "1075000002", "Bruno Díaz")
    for _ in range(3):
        armar.rostro(conexion, ana)
    armar.rostro(conexion, bruno)

    respuesta = sesion.delete(rostros_de(ana))

    assert respuesta.status_code == 204, respuesta.text
    assert respuesta.content == b""
    assert (armar.contar(conexion, "rostro", ana), armar.contar(conexion, "rostro", bruno)) == (0, 1)
    assert sesion.get(f"/api/v1/personas/{ana}").json()["muestras"] == 0  # la ficha ya no las cuenta (RF-12 · C3)


@pytest.mark.marca("RF-12 · C1")
def test_borrar_una_huella(sesion: TestClient, conexion: Connection) -> None:
    ana = armar.persona(conexion)
    queda = armar.rostro(conexion, ana)
    se_va = armar.rostro(conexion, ana)

    respuesta = sesion.delete(f"/api/v1/rostros/{se_va}")

    assert respuesta.status_code == 204, respuesta.text
    assert [rostro["id"] for rostro in sesion.get(rostros_de(ana)).json()] == [str(queda)]
    error(sesion.delete(f"/api/v1/rostros/{se_va}"), 404, "no_encontrado")  # ya no existe


# --- contrato API · listarRostros, borrarRostros y borrarRostro ---


@pytest.mark.marca("contrato API · listarRostros")
def test_listar_las_muestras_sin_la_huella_en_orden_de_creacion(sesion: TestClient, conexion: Connection) -> None:
    ana = armar.persona(conexion)
    bruno = armar.persona(conexion, "1075000002", "Bruno Díaz")
    segunda = armar.rostro(conexion, ana, calidad=95.5, creado=datetime(2026, 11, 12, 10, 0, tzinfo=BOGOTA))
    primera = armar.rostro(conexion, ana, calidad=None, creado=datetime(2026, 11, 12, 9, 0, tzinfo=BOGOTA))
    armar.rostro(conexion, bruno)

    respuesta = sesion.get(rostros_de(ana))

    assert respuesta.status_code == 200, respuesta.text
    for rostro in respuesta.json():
        validar("RostroResumen", rostro)
    assert respuesta.json() == [
        {
            "id": str(primera),
            "fuente": "simulador",
            "modelo": "sface_2021dec",
            "calidad": None,
            "creado": "2026-11-12T09:00:00-05:00",
        },
        {
            "id": str(segunda),
            "fuente": "simulador",
            "modelo": "sface_2021dec",
            "calidad": 95.5,
            "creado": "2026-11-12T10:00:00-05:00",
        },
    ]


@pytest.mark.marca("contrato API · listarRostros")
def test_una_persona_sin_muestras_da_una_lista_vacia(sesion: TestClient, conexion: Connection) -> None:
    ana = armar.persona(conexion)

    respuesta = sesion.get(rostros_de(ana))

    assert (respuesta.status_code, respuesta.json()) == (200, [])


@pytest.mark.marca("contrato API · listarRostros")
@pytest.mark.parametrize("persona_id", [str(uuid4()), "no-es-un-uuid"], ids=["que no existe", "que no es uuid"])
def test_listar_las_muestras_de_una_persona_que_no_existe_da_404(sesion: TestClient, persona_id: str) -> None:
    error(sesion.get(rostros_de(persona_id)), 404, "no_encontrado")


@pytest.mark.marca("contrato API · borrarRostros")
def test_borrar_las_huellas_de_quien_no_tiene_da_204(sesion: TestClient, conexion: Connection) -> None:
    ana = armar.persona(conexion)

    assert sesion.delete(rostros_de(ana)).status_code == 204


@pytest.mark.marca("contrato API · borrarRostros")
@pytest.mark.parametrize("persona_id", [str(uuid4()), "no-es-un-uuid"], ids=["que no existe", "que no es uuid"])
def test_borrar_las_huellas_de_una_persona_que_no_existe_da_404(sesion: TestClient, persona_id: str) -> None:
    error(sesion.delete(rostros_de(persona_id)), 404, "no_encontrado")


@pytest.mark.marca("contrato API · borrarRostro")
@pytest.mark.parametrize("rostro_id", [str(uuid4()), "no-es-un-uuid"], ids=["que no existe", "que no es uuid"])
def test_borrar_una_muestra_que_no_existe_da_404(sesion: TestClient, rostro_id: str) -> None:
    error(sesion.delete(f"/api/v1/rostros/{rostro_id}"), 404, "no_encontrado")
