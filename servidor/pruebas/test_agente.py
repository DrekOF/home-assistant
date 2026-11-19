"""
Nombre: test_agente.py
Descripción: Pruebas «contrato agente · <herramienta>», «contrato agente · preguntas» y «RNF-01 · C4»: las seis herramientas del agente con los datos de la semilla y el usuario agente, sin modelo.
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.1

Hoy es el viernes 2026-11-20 a las 10:00 (hora_fija.HOY): ayer es el 19 y antier, el 18.
"""

import json
from datetime import UTC, datetime
from typing import Any

import armar
import pytest
from hora_fija import HOY, ahora_fijo
from sqlalchemy import Connection, Engine, create_engine

from accesia import agente, semilla
from accesia.agente import Herramientas
from accesia.asistencia import registrar_llegada

pytestmark = pytest.mark.usefixtures("semilla_confirmada")

CLASE = "Clase todos los días"
VARIAS = {"mensaje": "Hay varias personas con ese nombre; pregunta cuál."}

AYER = {
    "fecha": "2026-11-19",
    "a_tiempo": [{"nombre": "Ana Gómez", "llegada": "06:58"}, {"nombre": "Bruno Díaz", "llegada": "07:05"}],
    "tarde": [{"nombre": "Carla Ruiz", "llegada": "07:12", "minutos_tarde": 12}],
    "sin_horario": [{"nombre": "David Peña", "llegada": "07:40"}],
    "ausentes": ["Felipe Soto"],
    "total_llegadas": 4,
}
ANTIER = {
    "fecha": "2026-11-18",
    "a_tiempo": [{"nombre": "Bruno Díaz", "llegada": "06:50"}, {"nombre": "Carla Ruiz", "llegada": "07:00"}],
    "tarde": [
        {"nombre": "Felipe Soto", "llegada": "07:11", "minutos_tarde": 11},
        {"nombre": "Ana Gómez", "llegada": "07:20", "minutos_tarde": 20},
    ],
    "sin_horario": [],
    "ausentes": [],
    "total_llegadas": 4,
}


def marca(herramienta: str) -> pytest.MarkDecorator:
    return pytest.mark.marca(f"contrato agente · {herramienta}")


@pytest.fixture
def herramientas(semilla_confirmada: Engine) -> Herramientas:
    """Las herramientas tal como las usa el servidor MCP: con el usuario agente y una transacción por llamada."""
    return Herramientas(semilla_confirmada)


def _es_error(respuesta: dict[str, Any]) -> bool:
    return set(respuesta) == {"error"} and isinstance(respuesta["error"], str) and respuesta["error"]


# --- buscar_persona ---


@marca("buscar_persona")
def test_buscar_persona_dice_rol_si_esta_activa_y_horario(herramientas: Herramientas) -> None:
    assert herramientas.buscar_persona("Elena Mora") == {
        "personas": [{"nombre": "Elena Mora", "rol": "estudiante", "activa": False, "horario": CLASE}]
    }


@marca("buscar_persona")
@pytest.mark.parametrize("buscado", ["pena", "PEÑA", "  david   peña ", "Peña"])
def test_buscar_persona_sin_importar_tildes_ni_mayusculas(herramientas: Herramientas, buscado: str) -> None:
    """Sin horario, «horario» va en null (mcp-agente.md 1.3)."""
    assert herramientas.buscar_persona(buscado) == {
        "personas": [{"nombre": "David Peña", "rol": "docente", "activa": True, "horario": None}]
    }


@marca("buscar_persona")
def test_buscar_persona_por_parte_del_nombre_en_orden(herramientas: Herramientas) -> None:
    nombres = [persona["nombre"] for persona in herramientas.buscar_persona("na")["personas"]]

    assert nombres == ["Ana Gómez", "David Peña", "Elena Mora"]


@marca("buscar_persona")
def test_buscar_persona_sin_resultados(herramientas: Herramientas) -> None:
    assert herramientas.buscar_persona("Zoe Vargas") == {"personas": []}


@marca("buscar_persona")
@pytest.mark.parametrize("nombre", ["a", "", "   ", "x" * 61])
def test_buscar_persona_el_nombre_tiene_de_2_a_60_caracteres(herramientas: Herramientas, nombre: str) -> None:
    assert _es_error(herramientas.buscar_persona(nombre))


@marca("buscar_persona")
def test_buscar_persona_porcentaje_y_guion_bajo_se_buscan_como_texto(herramientas: Herramientas) -> None:
    assert herramientas.buscar_persona("%%") == {"personas": []}
    assert herramientas.buscar_persona("a_a") == {"personas": []}  # con _ como comodín, encontraría a «Ana»


@marca("buscar_persona")
def test_buscar_persona_devuelve_como_maximo_10(conexion: Connection) -> None:
    for numero in range(12):
        armar.persona(conexion, documento=f"10759900{numero:02d}", nombre=f"Persona {numero:02d}")

    personas = agente.buscar_persona(conexion, "persona")["personas"]

    assert [persona["nombre"] for persona in personas] == [f"Persona {numero:02d}" for numero in range(10)]


# --- asistencia_del_dia ---


@marca("asistencia_del_dia")
@pytest.mark.parametrize("fecha", ["ayer", "Ayer", " AYER ", "2026-11-19"])
def test_asistencia_del_dia_de_ayer(herramientas: Herramientas, fecha: str) -> None:
    """Elena está inactiva y David no tiene horario: no cuentan como ausentes."""
    assert herramientas.asistencia_del_dia(fecha) == AYER


@marca("asistencia_del_dia")
def test_asistencia_del_dia_de_antier(herramientas: Herramientas) -> None:
    assert herramientas.asistencia_del_dia("antier") == ANTIER


@marca("asistencia_del_dia")
def test_asistencia_del_dia_por_defecto_es_hoy(herramientas: Herramientas) -> None:
    assert herramientas.asistencia_del_dia() == {
        "fecha": "2026-11-20",
        "a_tiempo": [],
        "tarde": [],
        "sin_horario": [],
        "ausentes": ["Ana Gómez", "Bruno Díaz", "Carla Ruiz", "Felipe Soto"],
        "total_llegadas": 0,
    }


@marca("asistencia_del_dia")
def test_asistencia_del_dia_cuenta_las_llegadas_manuales(conexion: Connection) -> None:
    felipe = semilla.POR_DOCUMENTO["SEMILLA-06"].id
    registrar_llegada(conexion, felipe, HOY.replace(day=19, hour=8, minute=30), "manual")

    resultado = agente.asistencia_del_dia(conexion, "ayer")

    assert resultado["ausentes"] == []
    assert resultado["total_llegadas"] == 5
    assert {"nombre": "Felipe Soto", "llegada": "08:30", "minutos_tarde": 90} in resultado["tarde"]


@marca("asistencia_del_dia")
@pytest.mark.parametrize("fecha", ["mañana", "19/11/2026", "2026-13-01", "2026-11-31", "", "20261119", "anteayer"])
def test_asistencia_del_dia_con_una_fecha_mal_escrita(herramientas: Herramientas, fecha: str) -> None:
    assert _es_error(herramientas.asistencia_del_dia(fecha))


# --- llegadas_tarde ---


@marca("llegadas_tarde")
def test_llegadas_tarde_de_antier_y_ayer(herramientas: Herramientas) -> None:
    assert herramientas.llegadas_tarde("antier", "ayer") == {
        "desde": "2026-11-18",
        "hasta": "2026-11-19",
        "llegadas": [
            {"fecha": "2026-11-18", "nombre": "Felipe Soto", "llegada": "07:11", "minutos_tarde": 11},
            {"fecha": "2026-11-18", "nombre": "Ana Gómez", "llegada": "07:20", "minutos_tarde": 20},
            {"fecha": "2026-11-19", "nombre": "Carla Ruiz", "llegada": "07:12", "minutos_tarde": 12},
        ],
        "total": 3,
    }


@marca("llegadas_tarde")
def test_llegadas_tarde_por_defecto_es_hoy(herramientas: Herramientas) -> None:
    assert herramientas.llegadas_tarde() == {"desde": "2026-11-20", "hasta": "2026-11-20", "llegadas": [], "total": 0}


@marca("llegadas_tarde")
def test_llegadas_tarde_hasta_31_dias_despues_de_desde(herramientas: Herramientas) -> None:
    assert herramientas.llegadas_tarde("2026-10-19", "2026-11-19")["total"] == 3
    assert _es_error(herramientas.llegadas_tarde("2026-10-18", "2026-11-19"))


@marca("llegadas_tarde")
@pytest.mark.parametrize(("desde", "hasta"), [("ayer", "antier"), ("hoy", "ayer"), ("ayer", "pasado"), ("x", "hoy")])
def test_llegadas_tarde_con_un_rango_mal_escrito(herramientas: Herramientas, desde: str, hasta: str) -> None:
    assert _es_error(herramientas.llegadas_tarde(desde, hasta))


# --- accesos_de_persona ---


def _acceso(fecha: str, hora: str, resultado: str = "permitido") -> dict[str, str]:
    return {"fecha": fecha, "hora": hora, "camara": "entrada", "resultado": resultado}


@marca("accesos_de_persona")
def test_accesos_de_persona_con_una_coincidencia(herramientas: Herramientas) -> None:
    assert herramientas.accesos_de_persona("Ana", "ayer", "ayer") == {
        "persona": "Ana Gómez",
        "accesos": [_acceso("2026-11-19", "06:58"), _acceso("2026-11-19", "09:30")],
        "total": 2,
    }


@marca("accesos_de_persona")
def test_accesos_de_persona_varios_dias_y_denegados(herramientas: Herramientas) -> None:
    assert herramientas.accesos_de_persona("ana gomez", "antier", "ayer")["accesos"] == [
        _acceso("2026-11-18", "07:20"), _acceso("2026-11-19", "06:58"), _acceso("2026-11-19", "09:30"),
    ]
    assert herramientas.accesos_de_persona("Elena", "ayer", "ayer")["accesos"] == [
        _acceso("2026-11-19", "07:45", "denegado")
    ]


@marca("accesos_de_persona")
def test_accesos_de_persona_por_defecto_es_hoy(herramientas: Herramientas) -> None:
    assert herramientas.accesos_de_persona("Ana") == {"persona": "Ana Gómez", "accesos": [], "total": 0}


@marca("accesos_de_persona")
def test_accesos_de_persona_con_varias_coincidencias(herramientas: Herramientas) -> None:
    assert herramientas.accesos_de_persona("na", "ayer", "ayer") == {
        "coincidencias": ["Ana Gómez", "David Peña", "Elena Mora"], **VARIAS
    }


@marca("accesos_de_persona")
def test_accesos_de_persona_sin_coincidencias(herramientas: Herramientas) -> None:
    assert herramientas.accesos_de_persona("Zoe Vargas") == {
        "coincidencias": [], "mensaje": "No hay nadie registrado con ese nombre."
    }


@marca("accesos_de_persona")
def test_accesos_de_persona_como_maximo_los_50_mas_recientes(conexion: Connection) -> None:
    """Con más de 50, van los 50 más recientes, en orden de hora, y total cuenta todos (mcp-agente.md 1.3)."""
    bruno = semilla.POR_DOCUMENTO["SEMILLA-02"].id
    for minuto in range(55):
        armar.evento(conexion, "entrada", bruno, fecha_hora=HOY.replace(hour=8, minute=minuto))

    resultado = agente.accesos_de_persona(conexion, "Bruno")

    assert resultado["total"] == 55
    assert len(resultado["accesos"]) == 50
    assert resultado["accesos"][0]["hora"] == "08:05"
    assert resultado["accesos"][-1]["hora"] == "08:54"


@marca("accesos_de_persona")
@pytest.mark.parametrize(("nombre", "desde", "hasta"), [("A", "hoy", "hoy"), ("Ana", "ayer", "antier"),
                                                         ("Ana", "el lunes", "hoy")])
def test_accesos_de_persona_con_datos_mal_escritos(herramientas: Herramientas, nombre: str, desde: str,
                                                  hasta: str) -> None:
    assert _es_error(herramientas.accesos_de_persona(nombre, desde, hasta))


# --- desconocidos_recientes ---


@marca("desconocidos_recientes")
def test_desconocidos_de_las_ultimas_24_horas(herramientas: Herramientas) -> None:
    esperado = {"horas": 24, "total": 3, "por_camara": {"entrada": 3}, "ultimos": ["2026-11-20 08:00"] * 3}

    assert herramientas.desconocidos_recientes(24) == esperado
    assert herramientas.desconocidos_recientes() == esperado  # 24 por defecto


@marca("desconocidos_recientes")
def test_desconocidos_de_las_ultimas_48_horas(herramientas: Herramientas) -> None:
    """ultimos va de la más antigua a la más nueva (mcp-agente.md 1.3)."""
    assert herramientas.desconocidos_recientes(48) == {
        "horas": 48,
        "total": 4,
        "por_camara": {"entrada": 4},
        "ultimos": ["2026-11-19 04:00", "2026-11-20 08:00", "2026-11-20 08:00", "2026-11-20 08:00"],
    }


@marca("desconocidos_recientes")
@pytest.mark.parametrize("horas", [0, 169, -1])
def test_desconocidos_horas_de_1_a_168(herramientas: Herramientas, horas: int) -> None:
    assert _es_error(herramientas.desconocidos_recientes(horas))


@marca("desconocidos_recientes")
def test_desconocidos_por_camara_y_10_en_ultimos(conexion: Connection) -> None:
    armar.camara(conexion, "patio")
    armar.evento(conexion, "patio", None, "desconocido", "bajo_umbral", 0.2, fecha_hora=HOY.replace(hour=9, minute=30))
    for minuto in range(12):
        armar.evento(conexion, "entrada", None, "desconocido", "bajo_umbral", 0.2,
                     fecha_hora=HOY.replace(hour=9, minute=minuto))

    resultado = agente.desconocidos_recientes(conexion, 24)

    assert resultado["total"] == 16
    assert resultado["por_camara"] == {"entrada": 15, "patio": 1}
    assert len(resultado["ultimos"]) == 10
    assert resultado["ultimos"][0] == "2026-11-20 09:03"
    assert resultado["ultimos"][-1] == "2026-11-20 09:30"


# --- fecha_y_hora_GetDateTime (mcp-agente.md 1.5) ---


@marca("fecha_y_hora_GetDateTime")
def test_fecha_y_hora_en_colombia(herramientas: Herramientas) -> None:
    assert herramientas.fecha_y_hora() == {"fecha": "2026-11-20", "dia": "viernes", "hora": "10:00"}


@marca("fecha_y_hora_GetDateTime")
def test_fecha_y_hora_cerca_de_la_medianoche_es_la_de_colombia(herramientas: Herramientas) -> None:
    # El sábado 21 a las 04:30 en UTC todavía es el viernes 20 a las 23:30 en Colombia (R8).
    with ahora_fijo(datetime(2026, 11, 21, 4, 30, 59, tzinfo=UTC)):
        assert herramientas.fecha_y_hora() == {"fecha": "2026-11-20", "dia": "viernes", "hora": "23:30"}


@marca("fecha_y_hora_GetDateTime")
def test_fecha_y_hora_no_toca_la_base() -> None:
    sin_base = Herramientas(create_engine("postgresql+psycopg://nadie@127.0.0.1:1/nada"))
    assert sin_base.fecha_y_hora() == {"fecha": "2026-11-20", "dia": "viernes", "hora": "10:00"}


# --- Las preguntas 1 a 9 de la evaluación ---


@pytest.mark.marca("contrato agente · preguntas")
@pytest.mark.parametrize("pregunta", semilla.PREGUNTAS, ids=lambda pregunta: f"pregunta {pregunta.numero}")
def test_la_herramienta_esperada_responde_bien(herramientas: Herramientas, pregunta: semilla.Pregunta) -> None:
    resultado = getattr(herramientas, pregunta.herramienta)(**pregunta.argumentos)

    assert pregunta.resumir(resultado) == pregunta.esperado


@pytest.mark.marca("contrato agente · preguntas")
def test_las_otras_herramientas_de_las_preguntas_1_y_3(herramientas: Herramientas) -> None:
    """La 1 también se responde con llegadas_tarde, y la 3 con accesos_de_persona."""
    assert herramientas.llegadas_tarde("ayer", "ayer")["llegadas"] == [
        {"fecha": "2026-11-19", "nombre": "Carla Ruiz", "llegada": "07:12", "minutos_tarde": 12}
    ]
    assert herramientas.accesos_de_persona("Ana", "ayer", "ayer")["accesos"][0]["hora"] == "06:58"


# --- RNF-01 · C4 ---


def _claves(valor: Any) -> set[str]:
    if isinstance(valor, dict):
        return set(valor) | {clave for hijo in valor.values() for clave in _claves(hijo)}
    if isinstance(valor, list):
        return {clave for hijo in valor for clave in _claves(hijo)}
    return set()


@pytest.mark.marca("RNF-01 · C4")
def test_ninguna_respuesta_trae_documentos_huellas_ni_similitudes(herramientas: Herramientas) -> None:
    respuestas = [
        herramientas.buscar_persona("na"),
        herramientas.buscar_persona("Elena"),
        herramientas.asistencia_del_dia("ayer"),
        herramientas.asistencia_del_dia("antier"),
        herramientas.llegadas_tarde("antier", "ayer"),
        herramientas.accesos_de_persona("Ana", "antier", "ayer"),
        herramientas.accesos_de_persona("Elena", "antier", "ayer"),
        herramientas.accesos_de_persona("na"),
        herramientas.desconocidos_recientes(168),
    ]
    texto = json.dumps(respuestas, ensure_ascii=False)

    assert not any("error" in respuesta for respuesta in respuestas)
    assert not _claves(respuestas) & {"documento", "huella", "similitud", "id", "persona_id"}
    assert "SEMILLA-" not in texto
    for evento in semilla.EVENTOS:  # ninguna similitud de la semilla aparece en las respuestas
        assert str(evento.similitud) not in texto
