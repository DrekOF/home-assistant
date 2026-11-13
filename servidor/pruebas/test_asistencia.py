"""
Nombre: test_asistencia.py
Descripción: Pruebas de la asistencia con la visión armada, el reloj de las pruebas y PostgreSQL real: los 15 casos de R5, R8 · fecha local, R4 sin cambiar la asistencia, RF-06 · C1 a C5, RF-12 · C3 y el contrato de verAsistencia, registrarAsistenciaManual, verAsistenciaPersona y exportarAsistencia.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import csv
import io
import logging
import threading
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import armar
import numpy as np
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from vision_falsa import CaraArmada, eje

from accesia.asistencia import Bloque, calificar_llegada, fecha_local, registrar_llegada
from accesia.reconocimiento import reconocer
from accesia.vision import Huella

BOGOTA = ZoneInfo("America/Bogota")
ASISTENCIA = "/api/v1/asistencia"

ANA = "Ana María Gómez"
BRUNO = "Bruno Díaz"
DAVID = "David Rojas"
ELENA = "Elena Ruiz"

# El bloque de «Clase IA», el horario de ejemplo de R5: de lunes a viernes a las 07:00, con 10 min de tolerancia.
CLASE_IA = Bloque(hora_inicio=time(7, 0), tolerancia_min=10)


def hora(dia: int, horas: int, minutos: int, segundos: int = 0) -> datetime:
    """Una hora de Colombia en la semana del lunes 16 de noviembre de 2026, la de los ejemplos de R5."""
    return datetime(2026, 11, dia, horas, minutos, segundos, tzinfo=BOGOTA)


def entra(camara, reloj, momento: datetime) -> dict:
    """La persona de eje(0) pasa por la cámara a esa hora."""
    reloj.momento = momento
    respuesta = camara.enviar(CaraArmada(huella=eje(0)))
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def la_llegada(conexion: Connection):
    """La única llegada guardada."""
    [llegada] = armar.llegadas(conexion)
    return llegada


def registrar(sesion: TestClient, persona_id, llegada: str):
    return sesion.post(ASISTENCIA, json={"persona_id": str(persona_id), "llegada": llegada})


def error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


def huella_fija(vector: list[float]):
    """El huella_de de reconocer() para llamarlo sin la API: siempre la misma huella, nítida."""

    def huella_de(_cara) -> Huella:
        return Huella(vector=np.asarray(vector, dtype=np.float32), nitidez=150.0)

    return huella_de


# --- R5 · Llegada y tardanza: la primera entrada permitida del día, por la cámara ---

CASOS_CLASE_IA = [
    pytest.param(hora(20, 6, 55), "a_tiempo", None, marks=pytest.mark.marca("R5 · temprano"), id="temprano"),
    pytest.param(hora(20, 7, 10, 0), "a_tiempo", None, marks=pytest.mark.marca("R5 · borde"), id="borde"),
    pytest.param(
        hora(20, 7, 10, 1), "tarde", 10, marks=pytest.mark.marca("R5 · un segundo tarde"), id="un segundo tarde"
    ),
    pytest.param(hora(20, 7, 25, 30), "tarde", 25, marks=pytest.mark.marca("R5 · tarde"), id="tarde"),
    pytest.param(hora(21, 8, 0), "sin_horario", None, marks=pytest.mark.marca("R5 · sábado"), id="sábado"),
]

CASOS_LUNES_Y_MIERCOLES = [
    pytest.param(
        hora(18, 18, 12), "a_tiempo", None, marks=pytest.mark.marca("R5 · bloque a tiempo"), id="bloque a tiempo"
    ),
    pytest.param(hora(18, 18, 20), "tarde", 20, marks=pytest.mark.marca("R5 · bloque tarde"), id="bloque tarde"),
    pytest.param(
        hora(17, 7, 5), "sin_horario", None, marks=pytest.mark.marca("R5 · día sin bloque"), id="día sin bloque"
    ),
]


@pytest.mark.parametrize(("momento", "estado", "minutos"), CASOS_CLASE_IA)
def test_la_primera_entrada_permitida_es_la_llegada(
    camaras, conexion: Connection, reloj, momento: datetime, estado: str, minutos: int | None
) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))

    cuerpo = entra(camara, reloj, momento)

    llegada = la_llegada(conexion)
    assert (llegada.persona_id, llegada.fecha, llegada.llegada) == (ana, momento.date(), momento)
    assert (llegada.estado, llegada.minutos_tarde) == (estado, minutos)
    assert (llegada.origen, str(llegada.evento_id), llegada.registrado_por) == ("camara", cuerpo["evento_id"], None)


@pytest.mark.parametrize(("momento", "estado", "minutos"), CASOS_CLASE_IA)
def test_calificar_llegada_con_el_bloque_de_clase_ia(momento: datetime, estado: str, minutos: int | None) -> None:
    # La función pura que usan la cámara, el registro manual y la semilla del agente. Clase IA no tiene bloque el sábado.
    bloque = CLASE_IA if momento.isoweekday() <= 5 else None

    calificacion = calificar_llegada(momento, bloque)

    assert (calificacion.estado, calificacion.minutos_tarde) == (estado, minutos)


@pytest.mark.parametrize(("momento", "estado", "minutos"), CASOS_LUNES_Y_MIERCOLES)
def test_cada_dia_se_califica_con_su_bloque(
    camaras, conexion: Connection, reloj, momento: datetime, estado: str, minutos: int | None
) -> None:
    camara = camaras()
    lunes_y_miercoles = armar.horario(conexion, "Lunes y miércoles", (1, "07:00", 10), (3, "18:00", 15))
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=lunes_y_miercoles)

    entra(camara, reloj, momento)

    llegada = la_llegada(conexion)
    assert (llegada.fecha, llegada.estado, llegada.minutos_tarde) == (momento.date(), estado, minutos)


@pytest.mark.marca("R5 · segunda entrada")
def test_una_segunda_entrada_no_cambia_la_llegada(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    primera = entra(camara, reloj, hora(20, 6, 55))

    segunda = entra(camara, reloj, hora(20, 9, 0))

    assert (segunda["resultado"], segunda["repetido"]) == ("permitido", False)
    assert len(armar.eventos(conexion)) == 2
    llegada = la_llegada(conexion)
    assert (llegada.llegada, llegada.estado, str(llegada.evento_id)) == (
        hora(20, 6, 55),
        "a_tiempo",
        primera["evento_id"],
    )


@pytest.mark.marca("R5 · sin horario")
def test_sin_horario_la_llegada_es_sin_horario(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, DAVID, "1075000004", eje(0))

    entra(camara, reloj, hora(20, 7, 30))

    llegada = la_llegada(conexion)
    assert (llegada.fecha, llegada.estado, llegada.minutos_tarde) == (date(2026, 11, 20), "sin_horario", None)


@pytest.mark.marca("R5 · denegado no cuenta")
def test_un_denegado_no_es_la_llegada(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    elena = armar.inscrita(conexion, ELENA, "1075000003", eje(0), activa=False, horario_id=armar.clase_ia(conexion))
    assert entra(camara, reloj, hora(20, 6, 50))["resultado"] == "denegado"
    assert armar.llegadas(conexion) == []

    conexion.execute(text("UPDATE persona SET activa = true WHERE id = :id"), {"id": elena})
    assert entra(camara, reloj, hora(20, 7, 20))["resultado"] == "permitido"

    llegada = la_llegada(conexion)
    assert (llegada.llegada, llegada.estado, llegada.minutos_tarde) == (hora(20, 7, 20), "tarde", 20)


@pytest.mark.marca("R5 · cerca de medianoche")
def test_cerca_de_medianoche_cuenta_la_fecha_de_colombia(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))

    entra(camara, reloj, datetime.fromisoformat("2026-11-20T23:30:00-05:00"))

    llegada = la_llegada(conexion)
    assert llegada.llegada.astimezone(UTC).date() == date(2026, 11, 21)  # en UTC ya es el 21
    assert (llegada.fecha, llegada.estado, llegada.minutos_tarde) == (date(2026, 11, 20), "tarde", 990)


@pytest.mark.marca("R5 · manual tarde")
def test_una_llegada_manual_tarde(sesion: TestClient, conexion: Connection, reloj, administrador: dict) -> None:
    reloj.momento = hora(20, 10, 0)
    ana = armar.persona(conexion, horario_id=armar.clase_ia(conexion))

    respuesta = registrar(sesion, ana, "2026-11-20T07:25:30-05:00")

    assert respuesta.status_code == 201, respuesta.text
    validar("Asistencia", respuesta.json())
    assert respuesta.json() == {
        "persona": {"id": str(ana), "nombre": ANA},
        "fecha": "2026-11-20",
        "llegada": "2026-11-20T07:25:30-05:00",
        "estado": "tarde",
        "minutos_tarde": 25,
        "origen": "manual",
        "registrado_por": administrador["nombre"],
    }
    llegada = la_llegada(conexion)
    assert (llegada.registrado_por, llegada.evento_id) == (administrador["id"], None)


@pytest.mark.marca("R5 · manual con llegada")
def test_registrar_a_mano_a_quien_ya_llego_da_409(camaras, sesion: TestClient, conexion: Connection, reloj) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    entra(camara, reloj, hora(20, 6, 55))
    reloj.momento = hora(20, 10, 0)

    respuesta = registrar(sesion, ana, "2026-11-20T07:30:00-05:00")

    error(respuesta, 409, "asistencia_duplicada")
    llegada = la_llegada(conexion)
    assert (llegada.llegada, llegada.origen) == (hora(20, 6, 55), "camara")


@pytest.mark.marca("R5 · cámara después de manual")
def test_la_camara_no_cambia_una_llegada_manual(camaras, sesion: TestClient, conexion: Connection, reloj) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    reloj.momento = hora(20, 7, 5)
    assert registrar(sesion, ana, "2026-11-20T07:05:00-05:00").status_code == 201

    cuerpo = entra(camara, reloj, hora(20, 7, 20))

    assert cuerpo["resultado"] == "permitido"
    llegada = la_llegada(conexion)
    assert (llegada.llegada, llegada.estado, llegada.origen, llegada.evento_id) == (
        hora(20, 7, 5),
        "a_tiempo",
        "manual",
        None,
    )


# --- R8 · Hora de Colombia ---


@pytest.mark.marca("R8 · fecha local")
def test_la_fecha_de_la_llegada_es_la_fecha_local(camaras, conexion: Connection, reloj) -> None:
    assert fecha_local(datetime.fromisoformat("2026-11-21T03:30:00Z")) == date(2026, 11, 20)
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))

    entra(camara, reloj, datetime.fromisoformat("2026-11-21T03:30:00Z"))

    assert la_llegada(conexion).fecha == date(2026, 11, 20)


# --- R4: una repetición no cambia la asistencia ---


@pytest.mark.marca("R4 · no cambia la asistencia")
def test_una_repeticion_no_crea_la_llegada_del_dia_siguiente(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    entra(camara, reloj, hora(20, 23, 59, 50))

    repetido = entra(camara, reloj, hora(20, 23, 59, 50) + timedelta(seconds=30))  # 00:00:20 del sábado 21

    assert repetido["repetido"] is True
    assert [llegada.fecha for llegada in armar.llegadas(conexion)] == [date(2026, 11, 20)]


# --- RF-06 · C1 y C2: la llegada desde la cámara y las entradas siguientes ---


@pytest.mark.marca("RF-06 · C1")
def test_reconocer_devuelve_la_llegada_que_creo_el_evento(conexion: Connection) -> None:
    # B2 publica estado y minutos_tarde en el campo asistencia del Evento (mqtt.md).
    armar.camara(conexion)
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    caras = [CaraArmada(huella=eje(0)).cara()]

    respuesta, _, llegada = reconocer(conexion, "entrada", caras, huella_fija(eje(0)), hora(20, 7, 25, 30))

    assert (respuesta.resultado, respuesta.repetido) == ("permitido", False)
    assert (llegada.persona_id, llegada.fecha, llegada.llegada) == (ana, date(2026, 11, 20), hora(20, 7, 25, 30))
    assert (llegada.estado, llegada.minutos_tarde, llegada.origen) == ("tarde", 25, "camara")
    assert la_llegada(conexion).evento_id == respuesta.evento_id


@pytest.mark.marca("RF-06 · C1")
def test_el_registro_de_la_camara_dice_la_llegada(camaras, conexion: Connection, reloj, caplog) -> None:
    caplog.set_level(logging.INFO, logger="accesia")
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))

    entra(camara, reloj, hora(20, 7, 25, 30))
    entra(camara, reloj, hora(20, 9, 0))

    lineas = [registro.getMessage() for registro in caplog.records if registro.getMessage().startswith("Cámara")]
    assert len(lineas) == 2
    assert "llegada tarde 25 min" in lineas[0]
    assert "llegada" not in lineas[1]


@pytest.mark.marca("RF-06 · C2")
def test_las_entradas_siguientes_no_devuelven_llegada(conexion: Connection) -> None:
    armar.camara(conexion)
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    caras = [CaraArmada(huella=eje(0)).cara()]
    huella_de = huella_fija(eje(0))
    _, _, primera = reconocer(conexion, "entrada", caras, huella_de, hora(20, 6, 55))

    repetida, _, llegada_repetida = reconocer(conexion, "entrada", caras, huella_de, hora(20, 6, 55, 30))
    otra, _, llegada_otra = reconocer(conexion, "entrada", caras, huella_de, hora(20, 9, 0))

    assert primera is not None
    assert (repetida.repetido, llegada_repetida) == (True, None)
    assert (otra.resultado, otra.repetido, llegada_otra) == ("permitido", False, None)
    assert len(armar.llegadas(conexion)) == 1


# --- RF-06 · C3: el reporte del día ---


@pytest.mark.marca("RF-06 · C3")
def test_el_reporte_separa_a_tiempo_tarde_sin_horario_y_ausentes(
    sesion: TestClient, conexion: Connection, reloj, administrador: dict
) -> None:
    reloj.momento = hora(20, 12, 0)
    clase = armar.clase_ia(conexion)
    lunes_y_miercoles = armar.horario(conexion, "Lunes y miércoles", (1, "07:00", 10), (3, "18:00", 15))
    ana = armar.persona(conexion, "1075000001", ANA, horario_id=clase)
    bruno = armar.persona(conexion, "1075000002", BRUNO, horario_id=clase)
    david = armar.persona(conexion, "1075000004", DAVID)  # sin horario
    fabio = armar.persona(conexion, "1075000006", "Fabio Torres", horario_id=clase)
    carla = armar.persona(conexion, "1075000005", "Carla Pérez", horario_id=clase)  # llegó el jueves, no hoy
    angela = armar.persona(conexion, "1075000007", "Ángela Ríos", horario_id=clase)  # no llegó
    armar.persona(conexion, "1075000003", ELENA, horario_id=clase, activa=False)  # inactiva: no es ausente
    armar.persona(conexion, "1075000008", "Gloria Vélez", horario_id=lunes_y_miercoles)  # sin bloque el viernes
    registrar_llegada(conexion, bruno, hora(20, 7, 25, 30), "camara")
    registrar_llegada(conexion, ana, hora(20, 6, 55), "camara")
    registrar_llegada(conexion, david, hora(20, 7, 30), "camara")
    registrar_llegada(conexion, fabio, hora(20, 7, 5), "manual", registrado_por=administrador["id"])
    registrar_llegada(conexion, carla, hora(19, 7, 0), "camara")

    respuesta = sesion.get(ASISTENCIA, params={"fecha": "2026-11-20"})

    assert respuesta.status_code == 200, respuesta.text
    reporte = respuesta.json()
    validar("ReporteAsistencia", reporte)
    assert reporte["fecha"] == "2026-11-20"
    assert [(fila["persona"]["nombre"], fila["llegada"], fila["origen"]) for fila in reporte["a_tiempo"]] == [
        (ANA, "2026-11-20T06:55:00-05:00", "camara"),
        ("Fabio Torres", "2026-11-20T07:05:00-05:00", "manual"),
    ]
    assert [fila["registrado_por"] for fila in reporte["a_tiempo"]] == [None, administrador["nombre"]]
    assert [(fila["persona"]["id"], fila["minutos_tarde"]) for fila in reporte["tarde"]] == [(str(bruno), 25)]
    assert [fila["persona"]["nombre"] for fila in reporte["sin_horario"]] == [DAVID]
    # Por nombre con la colación española: «Ángela» va antes de «Carla».
    assert reporte["ausentes"] == [
        {"id": str(angela), "nombre": "Ángela Ríos"},
        {"id": str(carla), "nombre": "Carla Pérez"},
    ]
    assert reporte["total_llegadas"] == 4


@pytest.mark.marca("contrato API · verAsistencia")
def test_sin_fecha_el_reporte_es_de_hoy_en_colombia(sesion: TestClient, conexion: Connection, reloj) -> None:
    reloj.momento = datetime.fromisoformat("2026-11-21T03:30:00Z")  # viernes 20 a las 22:30 en Colombia
    ana = armar.persona(conexion, horario_id=armar.clase_ia(conexion))

    respuesta = sesion.get(ASISTENCIA)

    assert respuesta.status_code == 200, respuesta.text
    validar("ReporteAsistencia", respuesta.json())
    assert respuesta.json() == {
        "fecha": "2026-11-20",
        "a_tiempo": [],
        "tarde": [],
        "sin_horario": [],
        "ausentes": [{"id": str(ana), "nombre": ANA}],
        "total_llegadas": 0,
    }


@pytest.mark.marca("contrato API · verAsistencia")
@pytest.mark.parametrize("fecha", ["20/11/2026", "2026-11-31", "hoy"])
def test_una_fecha_que_no_sirve_da_422(sesion: TestClient, fecha: str) -> None:
    error(sesion.get(ASISTENCIA, params={"fecha": fecha}), 422, "validacion")


# --- RF-06 · C5: el registro manual ---


@pytest.mark.marca("RF-06 · C5")
def test_registrar_a_mano_a_una_persona_que_no_existe_da_404(sesion: TestClient, reloj) -> None:
    reloj.momento = hora(20, 10, 0)

    error(registrar(sesion, uuid4(), "2026-11-20T07:00:00-05:00"), 404, "no_encontrado")


@pytest.mark.marca("RF-06 · C5")
def test_una_hora_futura_da_422(sesion: TestClient, conexion: Connection, reloj) -> None:
    reloj.momento = hora(20, 7, 0)
    ana = armar.persona(conexion, horario_id=armar.clase_ia(conexion))

    error(registrar(sesion, ana, "2026-11-20T07:00:01-05:00"), 422, "validacion")
    assert armar.llegadas(conexion) == []
    assert registrar(sesion, ana, "2026-11-20T07:00:00-05:00").status_code == 201  # la hora de ahora sí vale


@pytest.mark.marca("RF-06 · C5")
def test_una_persona_inactiva_tambien_se_registra_a_mano(sesion: TestClient, conexion: Connection, reloj) -> None:
    reloj.momento = hora(20, 10, 0)
    elena = armar.persona(conexion, "1075000003", ELENA, horario_id=armar.clase_ia(conexion), activa=False)

    respuesta = registrar(sesion, elena, "2026-11-20T06:58:00-05:00")

    assert respuesta.status_code == 201, respuesta.text
    assert (respuesta.json()["estado"], respuesta.json()["origen"]) == ("a_tiempo", "manual")


@pytest.mark.marca("RF-06 · C5")
def test_dos_registros_a_la_vez_dejan_una_sola_llegada(motor: Engine) -> None:
    """La segunda transacción espera a que la primera confirme y no escribe nada: la API responde 409 con None."""
    with motor.begin() as conexion:
        persona_id = armar.persona(conexion, "1075009999", "Persona Concurrente")
    try:
        with motor.connect() as primera, motor.connect() as segunda:
            segunda.execute(text("SET LOCAL lock_timeout = '5s'"))
            assert registrar_llegada(primera, persona_id, hora(20, 7, 0), "manual") is not None
            resultado: dict = {}

            def registrar_en_la_segunda() -> None:
                try:
                    resultado["llegada"] = registrar_llegada(segunda, persona_id, hora(20, 7, 5), "manual")
                except Exception as falla:  # se muestra en la falla de la prueba
                    resultado["falla"] = falla

            hilo = threading.Thread(target=registrar_en_la_segunda)
            hilo.start()
            hilo.join(timeout=0.5)
            assert hilo.is_alive(), f"La segunda no esperó a la primera: {resultado}"
            primera.commit()
            hilo.join(timeout=5)

            assert not hilo.is_alive()
            assert resultado == {"llegada": None}
            segunda.commit()
        with motor.connect() as conexion:
            llegadas = conexion.execute(
                text("SELECT llegada FROM asistencia WHERE persona_id = :id"), {"id": persona_id}
            ).scalars().all()
        assert llegadas == [hora(20, 7, 0)]
    finally:
        with motor.begin() as conexion:
            conexion.execute(text("DELETE FROM persona WHERE id = :id"), {"id": persona_id})


@pytest.mark.marca("contrato API · registrarAsistenciaManual")
def test_la_hora_puede_venir_en_otra_zona_y_se_guarda_sin_microsegundos(
    sesion: TestClient, conexion: Connection, reloj
) -> None:
    reloj.momento = hora(20, 10, 0)
    ana = armar.persona(conexion, horario_id=armar.clase_ia(conexion))

    respuesta = registrar(sesion, ana, "2026-11-20T12:25:30.750Z")

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    validar("Asistencia", cuerpo)
    assert (cuerpo["fecha"], cuerpo["llegada"], cuerpo["estado"], cuerpo["minutos_tarde"]) == (
        "2026-11-20",
        "2026-11-20T07:25:30-05:00",
        "tarde",
        25,
    )
    assert la_llegada(conexion).llegada == hora(20, 7, 25, 30)


@pytest.mark.marca("contrato API · registrarAsistenciaManual")
@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"persona_id": "no-es-un-uuid", "llegada": "2026-11-20T07:00:00-05:00"},
        {"persona_id": str(uuid4())},
        {"persona_id": str(uuid4()), "llegada": "2026-11-20T07:00:00"},
        {"persona_id": str(uuid4()), "llegada": "20/11/2026 07:00"},
    ],
    ids=["vacío", "persona que no es uuid", "sin llegada", "llegada sin zona", "llegada en otro formato"],
)
def test_un_cuerpo_que_no_sirve_da_422(sesion: TestClient, cuerpo: dict) -> None:
    error(sesion.post(ASISTENCIA, json=cuerpo), 422, "validacion")


# --- RF-12 · C3: la asistencia de una persona ---


@pytest.mark.marca("RF-12 · C3")
def test_las_llegadas_de_una_persona_van_de_la_mas_reciente_a_la_mas_antigua(
    sesion: TestClient, conexion: Connection
) -> None:
    clase = armar.clase_ia(conexion)
    ana = armar.persona(conexion, horario_id=clase)
    bruno = armar.persona(conexion, "1075000002", BRUNO, horario_id=clase)
    david = armar.persona(conexion, "1075000004", DAVID)
    for momento in (hora(16, 6, 58), hora(20, 7, 12), hora(18, 7, 0)):
        registrar_llegada(conexion, ana, momento, "camara")
    registrar_llegada(conexion, bruno, hora(19, 7, 0), "camara")

    def llegadas(persona_id=ana, **filtros) -> list[dict]:
        respuesta = sesion.get(f"/api/v1/personas/{persona_id}/asistencia", params=filtros)
        assert respuesta.status_code == 200, respuesta.text
        for llegada in respuesta.json():
            validar("Asistencia", llegada)
        return respuesta.json()

    def fechas(**filtros) -> list[str]:
        return [llegada["fecha"] for llegada in llegadas(**filtros)]

    assert fechas() == ["2026-11-20", "2026-11-18", "2026-11-16"]
    assert fechas(desde="2026-11-18") == ["2026-11-20", "2026-11-18"]
    assert fechas(hasta="2026-11-18") == ["2026-11-18", "2026-11-16"]
    assert fechas(desde="2026-11-17", hasta="2026-11-19") == ["2026-11-18"]
    assert fechas(desde="2026-11-20", hasta="2026-11-20") == ["2026-11-20"]
    assert llegadas(desde="2026-11-20") == [
        {
            "persona": {"id": str(ana), "nombre": ANA},
            "fecha": "2026-11-20",
            "llegada": "2026-11-20T07:12:00-05:00",
            "estado": "tarde",
            "minutos_tarde": 12,
            "origen": "camara",
            "registrado_por": None,
        }
    ]
    assert llegadas(persona_id=david) == []


@pytest.mark.marca("contrato API · verAsistenciaPersona")
@pytest.mark.parametrize("persona_id", [str(uuid4()), "no-es-un-uuid"], ids=["que no existe", "que no es uuid"])
def test_la_asistencia_de_una_persona_que_no_existe_da_404(sesion: TestClient, persona_id: str) -> None:
    error(sesion.get(f"/api/v1/personas/{persona_id}/asistencia"), 404, "no_encontrado")


@pytest.mark.marca("contrato API · verAsistenciaPersona")
@pytest.mark.parametrize(
    "filtros",
    [{"desde": "2026-11-20", "hasta": "2026-11-19"}, {"desde": "20/11/2026"}, {"hasta": "mañana"}],
    ids=["desde después de hasta", "desde en otro formato", "hasta que no es fecha"],
)
def test_un_rango_que_no_sirve_da_422(sesion: TestClient, conexion: Connection, filtros: dict) -> None:
    ana = armar.persona(conexion)

    error(sesion.get(f"/api/v1/personas/{ana}/asistencia", params=filtros), 422, "validacion")


# --- RF-06 · C4 (extra): exportar a CSV ---

CSV = "/api/v1/asistencia.csv"


@pytest.mark.marca("RF-06 · C4")
def test_exportar_un_rango_de_fechas_a_csv(sesion: TestClient, conexion: Connection, administrador: dict) -> None:
    clase = armar.clase_ia(conexion)
    ana = armar.persona(conexion, "1075000001", ANA, horario_id=clase)
    bruno = armar.persona(conexion, "1075000002", BRUNO, horario_id=clase)
    registrar_llegada(conexion, ana, hora(16, 6, 58), "camara")
    registrar_llegada(conexion, bruno, hora(18, 7, 25, 30), "manual", registrado_por=administrador["id"])
    registrar_llegada(conexion, ana, hora(18, 7, 0), "camara")
    registrar_llegada(conexion, ana, hora(20, 7, 0), "camara")  # fuera del rango

    respuesta = sesion.get(CSV, params={"desde": "2026-11-16", "hasta": "2026-11-18"})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "text/csv; charset=utf-8"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="asistencia-2026-11-16-a-2026-11-18.csv"'
    assert respuesta.content.decode("utf-8").splitlines() == [
        "fecha,nombre,documento,llegada,estado,minutos_tarde,origen",
        "2026-11-16,Ana María Gómez,1075000001,2026-11-16T06:58:00-05:00,a_tiempo,,camara",
        "2026-11-18,Ana María Gómez,1075000001,2026-11-18T07:00:00-05:00,a_tiempo,,camara",
        "2026-11-18,Bruno Díaz,1075000002,2026-11-18T07:25:30-05:00,tarde,25,manual",
    ]
    vacio = sesion.get(CSV, params={"desde": "2026-11-21", "hasta": "2026-11-22"})
    assert vacio.text.splitlines() == ["fecha,nombre,documento,llegada,estado,minutos_tarde,origen"]


@pytest.mark.marca("RF-06 · C4")
def test_un_texto_que_parece_formula_no_se_ejecuta_en_la_hoja_de_calculo(
    sesion: TestClient, conexion: Connection
) -> None:
    persona = armar.persona(conexion, "-A1", '=HIPERVINCULO("http://ejemplo.invalid")')
    registrar_llegada(conexion, persona, hora(20, 7, 0), "camara")

    respuesta = sesion.get(CSV, params={"desde": "2026-11-20", "hasta": "2026-11-20"})

    [_, fila] = list(csv.reader(io.StringIO(respuesta.text)))
    assert fila[1:3] == ["'=HIPERVINCULO(\"http://ejemplo.invalid\")", "'-A1"]


@pytest.mark.marca("contrato API · exportarAsistencia")
@pytest.mark.parametrize(
    "filtros",
    [
        {},
        {"desde": "2026-11-16"},
        {"desde": "2026-11-20", "hasta": "2026-11-16"},
        {"desde": "16/11/2026", "hasta": "2026-11-20"},
    ],
    ids=["sin fechas", "sin hasta", "desde después de hasta", "desde en otro formato"],
)
def test_exportar_sin_un_rango_valido_da_422(sesion: TestClient, filtros: dict) -> None:
    error(sesion.get(CSV, params=filtros), 422, "validacion")
