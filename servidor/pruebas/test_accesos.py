"""
Nombre: test_accesos.py
Descripción: Pruebas de la lista de accesos: RF-05 · C3 (filtros por fechas, resultado, persona y cámara, con paginación, del más reciente al más antiguo) y el contrato de listarAccesos.
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

ACCESOS = "/api/v1/accesos"
BOGOTA = ZoneInfo("America/Bogota")
ANA = "Ana María Gómez"
BRUNO = "Bruno Díaz"


def hora(dia: int, horas: int, minutos: int = 0) -> datetime:
    return datetime(2026, 11, dia, horas, minutos, tzinfo=BOGOTA)


@pytest.fixture
def accesos(conexion: Connection) -> dict:
    """Seis eventos en dos cámaras, con los tres resultados, del lunes 16 al viernes 20 de noviembre de 2026."""
    armar.camara(conexion, "entrada")
    armar.camara(conexion, "salida")
    ana = armar.persona(conexion, "1075000001", ANA)
    bruno = armar.persona(conexion, "1075000002", BRUNO)
    return {
        "ana": ana,
        "bruno": bruno,
        "ana_lunes": armar.evento(conexion, "entrada", ana, fecha_hora=hora(16, 7)),
        "desconocido_martes": armar.evento(
            conexion, "entrada", None, "desconocido", "bajo_umbral", 0.2, fecha_hora=hora(17, 8)
        ),
        "bruno_miercoles": armar.evento(conexion, "salida", bruno, "denegado", "inactiva", 0.6, fecha_hora=hora(18, 18)),
        "ana_jueves": armar.evento(conexion, "salida", ana, fecha_hora=hora(19, 12)),
        "desconocido_viernes": armar.evento(
            conexion, "entrada", None, "desconocido", "bajo_umbral", None, fecha_hora=hora(20, 6)
        ),
        "ana_viernes": armar.evento(conexion, "entrada", ana, fecha_hora=hora(20, 7)),
    }


def pagina(sesion: TestClient, **filtros) -> dict:
    respuesta = sesion.get(ACCESOS, params=filtros)
    assert respuesta.status_code == 200, respuesta.text
    validar("PaginaEventos", respuesta.json())
    return respuesta.json()


def ids(cuerpo: dict) -> list[str]:
    return [evento["id"] for evento in cuerpo["elementos"]]


def esperados(accesos: dict, *nombres: str) -> list[str]:
    return [str(accesos[nombre]) for nombre in nombres]


def error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


# --- RF-05 · C3: filtros y paginación ---


@pytest.mark.marca("RF-05 · C3")
def test_sin_filtros_van_todos_del_mas_reciente_al_mas_antiguo(sesion: TestClient, accesos: dict) -> None:
    cuerpo = pagina(sesion)

    assert ids(cuerpo) == esperados(
        accesos,
        "ana_viernes",
        "desconocido_viernes",
        "ana_jueves",
        "bruno_miercoles",
        "desconocido_martes",
        "ana_lunes",
    )
    assert (cuerpo["total"], cuerpo["pagina"], cuerpo["por_pagina"]) == (6, 1, 20)


@pytest.mark.marca("RF-05 · C3")
@pytest.mark.parametrize(
    ("filtros", "nombres"),
    [
        ({"resultado": "desconocido"}, ["desconocido_viernes", "desconocido_martes"]),
        ({"resultado": "denegado"}, ["bruno_miercoles"]),
        ({"dispositivo": "salida"}, ["ana_jueves", "bruno_miercoles"]),
        ({"persona": "ana"}, ["ana_viernes", "ana_jueves", "ana_lunes"]),
        ({"persona": "ana", "dispositivo": "entrada"}, ["ana_viernes", "ana_lunes"]),
        ({"persona": "ana", "resultado": "denegado"}, []),
    ],
    ids=["desconocidos", "denegados", "una cámara", "una persona", "persona y cámara", "persona sin denegados"],
)
def test_filtrar_por_resultado_persona_y_camara(
    sesion: TestClient, accesos: dict, filtros: dict, nombres: list[str]
) -> None:
    if "persona" in filtros:
        filtros["persona_id"] = str(accesos[filtros.pop("persona")])

    cuerpo = pagina(sesion, **filtros)

    assert ids(cuerpo) == esperados(accesos, *nombres)
    assert cuerpo["total"] == len(nombres)


@pytest.mark.marca("RF-05 · C3")
def test_desde_y_hasta_incluyen_sus_bordes(sesion: TestClient, accesos: dict) -> None:
    cuerpo = pagina(sesion, desde="2026-11-18T18:00:00-05:00", hasta="2026-11-20T06:00:00-05:00")

    assert ids(cuerpo) == esperados(accesos, "desconocido_viernes", "ana_jueves", "bruno_miercoles")
    assert cuerpo["total"] == 3
    # La misma hora en otra zona: 23:00 UTC del miércoles son las 18:00 de Colombia.
    assert ids(pagina(sesion, desde="2026-11-18T23:00:00Z")) == ids(pagina(sesion, desde="2026-11-18T18:00:00-05:00"))


@pytest.mark.marca("RF-05 · C3")
def test_paginar_conserva_el_orden_y_el_total(sesion: TestClient, accesos: dict) -> None:
    segunda = pagina(sesion, pagina=2, por_pagina=2)
    despues_del_final = pagina(sesion, pagina=4, por_pagina=2)

    assert ids(segunda) == esperados(accesos, "ana_jueves", "bruno_miercoles")
    assert (segunda["total"], segunda["pagina"], segunda["por_pagina"]) == (6, 2, 2)
    assert (despues_del_final["elementos"], despues_del_final["total"]) == ([], 6)


@pytest.mark.marca("RF-05 · C3")
def test_con_la_misma_hora_va_primero_el_ultimo_guardado(sesion: TestClient, conexion: Connection) -> None:
    armar.camara(conexion, "entrada")
    ana = armar.persona(conexion)
    primero = armar.evento(conexion, "entrada", ana, fecha_hora=hora(20, 7))
    segundo = armar.evento(conexion, "entrada", None, "desconocido", "bajo_umbral", 0.1, fecha_hora=hora(20, 7))

    assert ids(pagina(sesion)) == [str(segundo), str(primero)]


@pytest.mark.marca("RF-05 · C3")
@pytest.mark.parametrize("filtro", ["persona_id", "dispositivo"])
def test_una_persona_o_camara_que_no_existe_da_una_pagina_vacia(
    sesion: TestClient, accesos: dict, filtro: str
) -> None:
    valor = str(uuid4()) if filtro == "persona_id" else "porteria"

    cuerpo = pagina(sesion, **{filtro: valor})

    assert (cuerpo["elementos"], cuerpo["total"]) == ([], 0)


# --- contrato API · listarAccesos ---


@pytest.mark.marca("contrato API · listarAccesos")
def test_cada_evento_lleva_los_campos_del_contrato(sesion: TestClient, accesos: dict) -> None:
    elementos = {evento["id"]: evento for evento in pagina(sesion)["elementos"]}

    assert elementos[str(accesos["ana_lunes"])] == {
        "id": str(accesos["ana_lunes"]),
        "fecha_hora": "2026-11-16T07:00:00-05:00",
        "dispositivo": "entrada",
        "resultado": "permitido",
        "motivo": None,
        "persona": {"id": str(accesos["ana"]), "nombre": ANA},
        "similitud": pytest.approx(0.71, abs=1e-6),
    }
    denegado = elementos[str(accesos["bruno_miercoles"])]
    assert (denegado["resultado"], denegado["motivo"], denegado["persona"]["nombre"]) == ("denegado", "inactiva", BRUNO)
    # Un desconocido no lleva persona (RNF-01 · C3); su similitud puede ser nula si no había muestras.
    desconocido = elementos[str(accesos["desconocido_viernes"])]
    assert (desconocido["persona"], desconocido["motivo"], desconocido["similitud"]) == (None, "bajo_umbral", None)


@pytest.mark.marca("contrato API · listarAccesos")
@pytest.mark.parametrize(
    "filtros",
    [
        {"pagina": "0"},
        {"por_pagina": "0"},
        {"por_pagina": "101"},
        {"resultado": "descartado"},
        {"persona_id": "no-es-un-uuid"},
        {"dispositivo": "AB"},
        {"desde": "2026-11-20T07:00:00"},
        {"hasta": "ayer"},
        {"desde": "2026-11-20T07:00:01-05:00", "hasta": "2026-11-20T07:00:00-05:00"},
    ],
    ids=[
        "página 0",
        "por página 0",
        "por página 101",
        "resultado que no es de acceso",
        "persona que no es uuid",
        "cámara con mayúsculas",
        "desde sin zona",
        "hasta que no es fecha",
        "desde después de hasta",
    ],
)
def test_un_filtro_que_no_sirve_da_422(sesion: TestClient, filtros: dict) -> None:
    error(sesion.get(ACCESOS, params=filtros), 422, "validacion")
