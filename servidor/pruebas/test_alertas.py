"""
Nombre: test_alertas.py
Descripción: Pruebas de la alerta de desconocidos (R6) por la cámara, con el reloj de las pruebas y Mosquitto en un contenedor: los siete casos de la regla y el contrato del mensaje Alerta.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import armar
import pytest
from mqtt_de_prueba import retenidos
from sqlalchemy import Connection
from vision_falsa import CaraArmada, eje, parecida

from accesia.mqtt import Publicacion

BOGOTA = ZoneInfo("America/Bogota")
INICIO = datetime(2026, 11, 20, 8, 15, 0, tzinfo=BOGOTA)


def en(segundos: float) -> datetime:
    return INICIO + timedelta(seconds=segundos)


def alertas(servidor, escucha, codigo: str = "entrada") -> list[dict]:
    """Las alertas que llegaron a la cámara, después de una marca que asegura que ya llegó todo lo anterior."""
    carga = uuid.uuid4().hex
    assert servidor.publicar(Publicacion("accesia/prueba/marca", carga, 1, False))
    escucha.esperar("accesia/prueba/marca", lambda mensaje: mensaje.carga == carga)
    return [mensaje.json() for mensaje in escucha.mensajes(f"accesia/{codigo}/alerta")]


def desconocidos(camara, reloj, *segundos: float) -> None:
    """Una cara que no es de nadie en cada instante (t = segundos desde INICIO)."""
    for t in segundos:
        reloj.momento = en(t)
        cuerpo = camara.enviar(CaraArmada(huella=parecida(0.1))).json()
        assert cuerpo["resultado"] == "desconocido"


def horas(lista: list[dict]) -> list[str]:
    return [alerta["hora"] for alerta in lista]


@pytest.fixture
def entrada(camaras, conexion: Connection):
    """La cámara entrada, con Ana inscrita: eje(0) es ella (permitido) y parecida(0.1) es un desconocido."""
    armar.inscrita(conexion, "Ana María Gómez", "1075000001", eje(0))
    return camaras("entrada")


# --- R6 · Alerta de desconocidos ---


@pytest.mark.marca("R6 · tres en la ventana")
def test_tres_desconocidos_en_la_ventana_dan_una_alerta(entrada, reloj, mqtt_servidor, escucha) -> None:
    desconocidos(entrada, reloj, 0, 20, 50)

    assert horas(alertas(mqtt_servidor, escucha)) == [en(50).isoformat()]


@pytest.mark.marca("R6 · cuarto")
def test_el_cuarto_no_da_otra_alerta(entrada, reloj, mqtt_servidor, escucha) -> None:
    desconocidos(entrada, reloj, 0, 20, 50, 55)

    assert horas(alertas(mqtt_servidor, escucha)) == [en(50).isoformat()]


@pytest.mark.marca("R6 · después de la espera")
def test_pasada_la_ventana_de_la_ultima_alerta_vuelve_a_avisar(entrada, reloj, mqtt_servidor, escucha) -> None:
    desconocidos(entrada, reloj, 0, 20, 50, 55, 115, 120, 125)

    assert horas(alertas(mqtt_servidor, escucha)) == [en(50).isoformat(), en(125).isoformat()]


@pytest.mark.marca("R6 · fuera de la ventana")
def test_tres_desconocidos_que_no_caben_en_la_ventana_no_avisan(entrada, reloj, mqtt_servidor, escucha) -> None:
    desconocidos(entrada, reloj, 0, 30, 61)

    assert alertas(mqtt_servidor, escucha) == []


@pytest.mark.marca("R6 · borde")
def test_en_el_borde_el_primero_ya_no_cuenta(entrada, reloj, mqtt_servidor, escucha) -> None:
    desconocidos(entrada, reloj, 0, 30, 60)

    assert alertas(mqtt_servidor, escucha) == []


@pytest.mark.marca("R6 · mezclados")
def test_un_permitido_no_cuenta_como_desconocido(entrada, reloj, mqtt_servidor, escucha) -> None:
    desconocidos(entrada, reloj, 0, 10)
    reloj.momento = en(20)
    assert entrada.enviar(CaraArmada(huella=eje(0))).json()["resultado"] == "permitido"

    assert alertas(mqtt_servidor, escucha) == []


@pytest.mark.marca("R6 · dos cámaras")
def test_cada_camara_cuenta_sus_desconocidos(entrada, camaras, reloj, mqtt_servidor, escucha) -> None:
    salida = camaras("salida")
    desconocidos(entrada, reloj, 0, 10)
    desconocidos(salida, reloj, 20)

    assert alertas(mqtt_servidor, escucha, "entrada") == []
    assert alertas(mqtt_servidor, escucha, "salida") == []


@pytest.mark.marca("R6 · una alerta por ventana")
def test_no_se_repite_la_alerta_antes_de_la_ventana(entrada, reloj, mqtt_servidor, escucha) -> None:
    # R6: «salvo que la última alerta de esa cámara tenga menos de ALERTA_VENTANA_S segundos», aunque después de ella
    # ya se hayan juntado otros tres desconocidos.
    desconocidos(entrada, reloj, 0, 20, 50, 51, 52, 53, 110)

    assert horas(alertas(mqtt_servidor, escucha)) == [en(50).isoformat(), en(110).isoformat()]


# --- contrato MQTT · alerta ---


@pytest.mark.marca("contrato MQTT · alerta")
def test_la_alerta_sale_con_su_mensaje_qos_1_y_sin_retener(entrada, reloj, mqtt_servidor, escucha, broker_mqtt) -> None:
    desconocidos(entrada, reloj, 0, 20, 41)

    mensaje = escucha.esperar("accesia/entrada/alerta")
    assert (mensaje.qos, mensaje.retenido) == (1, False)
    assert mensaje.json() == {
        "dispositivo": "entrada",
        "desconocidos": 3,
        "ventana_s": 60,
        "hora": "2026-11-20T08:15:41-05:00",
    }
    assert retenidos(broker_mqtt, "accesia/entrada/alerta") == {}
