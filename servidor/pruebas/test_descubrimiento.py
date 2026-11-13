"""
Nombre: test_descubrimiento.py
Descripción: Pruebas del descubrimiento de Home Assistant con Mosquitto en un contenedor: los config de mqtt.md, cuándo se publican (RF-07 · C1, también desde crear-camara) y la limpieza de los de cámaras que ya no existen, sin tocar los de la placa.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import armar
import pytest
from fastapi.testclient import TestClient
from mqtt_de_prueba import ESPERA_S, ClienteDePrueba, retenidos, url_del_servidor
from sqlalchemy import Connection, text

from accesia import __version__
from accesia.comandos import principal
from accesia.config import configuracion
from accesia.mqtt import Publicacion

# Los config que pide mqtt.md, escritos aquí a partir del contrato y no del código del servidor.
DISPONIBLE_SERVIDOR = "accesia/servidor/disponible"
ORIGEN = {"name": "AccesIA servidor", "sw_version": __version__}


def dispositivo(codigo: str, nombre: str) -> dict:
    return {
        "identifiers": [f"accesia_{codigo}"],
        "name": f"AccesIA {nombre}",
        "manufacturer": "Equipo AccesIA",
        "model": "XIAO ESP32-C6",
        "sw_version": __version__,
    }


def configs_de_la_camara(codigo: str, nombre: str) -> dict[str, dict]:
    entidad = codigo.replace("-", "_")
    nodo = f"accesia_{codigo}"
    disponible_camara = f"accesia/{codigo}/disponible"
    comun = {"device": dispositivo(codigo, nombre), "origin": ORIGEN}

    def ids(componente: str, objeto: str) -> dict:
        unico = f"accesia_{entidad}_{objeto}"
        return {"unique_id": unico, "default_entity_id": f"{componente}.{unico}"}

    return {
        f"homeassistant/sensor/{nodo}/ultima_persona/config": {
            "name": "Última persona",
            **ids("sensor", "ultima_persona"),
            "state_topic": f"accesia/{codigo}/evento",
            "value_template": "{{ value_json.persona.nombre if value_json.persona else 'Desconocido' }}",
            "json_attributes_topic": f"accesia/{codigo}/evento",
            "icon": "mdi:account-badge",
            "availability_topic": DISPONIBLE_SERVIDOR,
            **comun,
        },
        f"homeassistant/sensor/{nodo}/ultimo_resultado/config": {
            "name": "Último resultado",
            **ids("sensor", "ultimo_resultado"),
            "state_topic": f"accesia/{codigo}/evento",
            "value_template": "{{ value_json.resultado }}",
            "availability_topic": DISPONIBLE_SERVIDOR,
            **comun,
        },
        f"homeassistant/binary_sensor/{nodo}/desconocido/config": {
            "name": "Desconocido detectado",
            **ids("binary_sensor", "desconocido"),
            "state_topic": f"accesia/{codigo}/alerta",
            "value_template": "{{ 'ON' }}",
            "off_delay": 60,
            "device_class": "problem",
            "availability_topic": DISPONIBLE_SERVIDOR,
            **comun,
        },
        f"homeassistant/binary_sensor/{nodo}/puerta/config": {
            "name": "Puerta",
            **ids("binary_sensor", "puerta"),
            "state_topic": f"accesia/{codigo}/puerta/estado",
            "payload_on": "abierta",
            "payload_off": "cerrada",
            "device_class": "door",
            "availability_topic": disponible_camara,
            **comun,
        },
        f"homeassistant/button/{nodo}/abrir_puerta/config": {
            "name": "Abrir puerta",
            **ids("button", "abrir_puerta"),
            "command_topic": f"accesia/{codigo}/puerta/set",
            "payload_press": "ABRIR",
            "availability_topic": disponible_camara,
            **comun,
        },
        f"homeassistant/binary_sensor/{nodo}/en_linea/config": {
            "name": "Cámara en línea",
            **ids("binary_sensor", "en_linea"),
            "state_topic": disponible_camara,
            "payload_on": "online",
            "payload_off": "offline",
            "device_class": "connectivity",
            **comun,
        },
    }


def configs_del_servidor() -> dict[str, dict]:
    comun = {
        "device": {
            "identifiers": ["accesia_servidor"],
            "name": "AccesIA Servidor",
            "manufacturer": "Equipo AccesIA",
            "sw_version": __version__,
        },
        "origin": ORIGEN,
    }

    def sensor(objeto: str, nombre: str, campo: str) -> dict:
        return {
            "name": nombre,
            "unique_id": f"accesia_{objeto}",
            "default_entity_id": f"sensor.accesia_{objeto}",
            "state_topic": "accesia/resumen",
            "value_template": "{{ value_json." + campo + " }}",
            "unit_of_measurement": "personas",
            "state_class": "measurement",
            "availability_topic": DISPONIBLE_SERVIDOR,
            **comun,
        }

    return {
        "homeassistant/sensor/accesia_servidor/asistentes_hoy/config": sensor("asistentes_hoy", "Asistentes hoy", "asistentes"),
        "homeassistant/sensor/accesia_servidor/tarde_hoy/config": sensor("tarde_hoy", "Llegadas tarde hoy", "tarde"),
        "homeassistant/sensor/accesia_servidor/desconocidos_hoy/config": sensor(
            "desconocidos_hoy", "Desconocidos hoy", "desconocidos_hoy"
        ),
        "homeassistant/binary_sensor/accesia_servidor/en_linea/config": {
            "name": "Servidor en línea",
            "unique_id": "accesia_servidor_en_linea",
            "default_entity_id": "binary_sensor.accesia_servidor_en_linea",
            "state_topic": DISPONIBLE_SERVIDOR,
            "payload_on": "online",
            "payload_off": "offline",
            "device_class": "connectivity",
            **comun,
        },
    }


def marcar(servidor, escucha) -> None:
    carga = uuid.uuid4().hex
    assert servidor.publicar(Publicacion("accesia/prueba/marca", carga, 1, False))
    escucha.esperar("accesia/prueba/marca", lambda mensaje: mensaje.carga == carga)


def configs_recibidos(escucha) -> set[str]:
    return {m.tema for m in escucha.mensajes() if m.tema.startswith("homeassistant/") and m.tema.endswith("/config")}


# --- contrato MQTT · descubrimiento ---


@pytest.mark.marca("contrato MQTT · descubrimiento")
def test_los_config_de_una_camara_y_del_servidor_son_los_del_contrato(
    conexion: Connection, conectar_mqtt, escucha, broker_mqtt
) -> None:
    armar.camara(conexion, "entrada")  # nombre «Entrada»
    esperados = {**configs_de_la_camara("entrada", "Entrada"), **configs_del_servidor()}

    servidor = conectar_mqtt()

    for tema, config in esperados.items():
        mensaje = escucha.esperar(tema)
        assert mensaje.qos == 1, tema
        assert mensaje.json() == config, tema
    marcar(servidor, escucha)
    assert configs_recibidos(escucha) == set(esperados)  # ni uno más
    assert set(retenidos(broker_mqtt, "homeassistant/#")) == set(esperados)  # todos retenidos


@pytest.mark.marca("contrato MQTT · descubrimiento")
def test_con_guiones_el_dispositivo_es_el_mismo_de_la_placa(conexion: Connection, conectar_mqtt, escucha) -> None:
    # La placa usa identifiers accesia_{codigo} con el código tal cual, y unique_id con guion bajo (PR #11).
    armar.camara(conexion, "puerta-norte")

    conectar_mqtt()

    for tema, config in configs_de_la_camara("puerta-norte", "Puerta-norte").items():
        assert escucha.esperar(tema).json() == config
    config = escucha.esperar("homeassistant/sensor/accesia_puerta-norte/ultima_persona/config").json()
    assert config["device"]["identifiers"] == ["accesia_puerta-norte"]
    assert config["unique_id"] == "accesia_puerta_norte_ultima_persona"


# --- RF-07 · C1: cuándo se publica ---


@pytest.mark.marca("RF-07 · C1")
def test_al_conectarse_publica_el_de_todas_las_camaras(conexion: Connection, conectar_mqtt, escucha) -> None:
    armar.camara(conexion, "entrada")
    armar.camara(conexion, "salida", tipo="tinyml", activo=False)

    conectar_mqtt()

    for codigo in ("entrada", "salida"):
        config = escucha.esperar(f"homeassistant/sensor/accesia_{codigo}/ultima_persona/config").json()
        assert config["device"]["model"] == "XIAO ESP32-C6"


@pytest.mark.marca("RF-07 · C1")
def test_cuando_home_assistant_vuelve_lo_publica_otra_vez(conexion: Connection, mqtt_servidor, escucha, broker_mqtt) -> None:
    armar.camara(conexion, "entrada")
    escucha.olvidar()

    home_assistant = ClienteDePrueba(broker_mqtt, "homeassistant").conectar()
    home_assistant.publicar("homeassistant/status", "online")
    home_assistant.cerrar()

    for tema in {**configs_de_la_camara("entrada", "Entrada"), **configs_del_servidor()}:
        escucha.esperar(tema)


@pytest.mark.marca("RF-07 · C1")
def test_home_assistant_offline_no_publica_nada(conexion: Connection, mqtt_servidor, escucha, broker_mqtt) -> None:
    armar.camara(conexion, "entrada")
    escucha.olvidar()

    home_assistant = ClienteDePrueba(broker_mqtt, "homeassistant").conectar()
    home_assistant.publicar("homeassistant/status", "offline")
    home_assistant.cerrar()

    marcar(mqtt_servidor, escucha)
    assert configs_recibidos(escucha) == set()


@pytest.mark.marca("RF-07 · C1")
def test_al_crear_o_editar_una_camara_por_la_api_publica_la_suya(sesion: TestClient, mqtt_servidor, escucha) -> None:
    escucha.olvidar()

    respuesta = sesion.post("/api/v1/dispositivos", json={"codigo": "porteria", "nombre": "Portería", "tipo": "simulador"})

    assert respuesta.status_code == 201, respuesta.text
    for tema, config in configs_de_la_camara("porteria", "Portería").items():
        assert escucha.esperar(tema).json() == config  # model «XIAO ESP32-C6» también para un simulador
    marcar(mqtt_servidor, escucha)
    assert configs_recibidos(escucha) == set(configs_de_la_camara("porteria", "Portería"))  # solo los suyos

    escucha.olvidar()
    respuesta = sesion.patch("/api/v1/dispositivos/porteria", json={"nombre": "Portería norte"})

    assert respuesta.status_code == 200, respuesta.text
    for tema, config in configs_de_la_camara("porteria", "Portería norte").items():
        assert escucha.esperar(tema).json() == config


@contextmanager
def comando_con_mqtt(conexion: Connection, monkeypatch: pytest.MonkeyPatch, url: str) -> Iterator[None]:
    """El comando escribe en la transacción de la prueba y usa esta MQTT_URL."""

    @contextmanager
    def transaccion() -> Iterator[Connection]:
        with conexion.begin_nested():
            yield conexion

    monkeypatch.setattr("accesia.db.transaccion", transaccion)
    monkeypatch.setenv("MQTT_URL", url)
    configuracion.cache_clear()
    try:
        yield
    finally:
        monkeypatch.delenv("MQTT_URL")
        configuracion.cache_clear()


@pytest.mark.marca("RF-07 · C1")
def test_crear_camara_publica_el_descubrimiento_de_la_camara(
    conexion: Connection, broker_mqtt, escucha, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    with comando_con_mqtt(conexion, monkeypatch, url_del_servidor(broker_mqtt)):
        codigo = principal(["crear-camara", "porteria", "--nombre", "Portería", "--tipo", "simulador"])

    assert codigo == 0
    for tema, config in configs_de_la_camara("porteria", "Portería").items():
        mensaje = escucha.esperar(tema)
        assert (mensaje.qos, mensaje.json()) == (1, config)
    salida = capsys.readouterr().out.strip().splitlines()
    assert any("Home Assistant" in linea for linea in salida)
    assert " " not in salida[-1], "La última línea sigue siendo solo el token."


@pytest.mark.marca("RF-07 · C1")
def test_crear_camara_sin_broker_crea_la_camara_y_avisa(
    conexion: Connection, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    with comando_con_mqtt(conexion, monkeypatch, "mqtt://servidor:clave@127.0.0.1:1"):
        codigo = principal(["crear-camara", "porteria", "--nombre", "Portería", "--tipo", "simulador"])

    assert codigo == 0
    assert conexion.execute(text("SELECT count(*) FROM dispositivo WHERE codigo = 'porteria'")).scalar_one() == 1
    salida = capsys.readouterr()
    assert "al reconectarse" in salida.err
    assert " " not in salida.out.strip().splitlines()[-1]


# --- contrato MQTT · limpieza del descubrimiento ---


@pytest.mark.marca("contrato MQTT · limpieza del descubrimiento")
def test_borra_los_config_de_camaras_que_ya_no_existen_y_nunca_los_de_la_placa(
    conexion: Connection, conectar_mqtt, escucha, broker_mqtt
) -> None:
    armar.camara(conexion, "entrada")
    de_camaras_borradas = [
        "homeassistant/sensor/accesia_vieja/ultima_persona/config",
        "homeassistant/button/accesia_vieja/abrir_puerta/config",
        "homeassistant/binary_sensor/accesia_otra-vieja/puerta/config",
    ]
    de_la_placa = [
        "homeassistant/sensor/vieja/temperatura/config",
        "homeassistant/sensor/vieja/humedad/config",
        "homeassistant/sensor/entrada/temperatura/config",
    ]
    # Uno viejo del servidor para una cámara que sí existe: la limpieza lo revisa y no lo borra.
    de_una_camara_que_existe = "homeassistant/sensor/accesia_entrada/ultima_persona/config"
    plantador = ClienteDePrueba(broker_mqtt, "homeassistant").conectar()
    for tema in [*de_camaras_borradas, *de_la_placa, de_una_camara_que_existe]:
        plantador.publicar(tema, '{"name": "de antes"}', retenido=True)
    plantador.cerrar()

    servidor = conectar_mqtt()

    for tema in de_camaras_borradas:
        mensaje = escucha.esperar(tema, lambda m: m.carga == "")  # un mensaje vacío retenido lo borra
        assert mensaje.qos == 1
    assert servidor.esperar_trabajo(ESPERA_S)  # ya revisó todos los retenidos, también el de entrada
    marcar(servidor, escucha)
    quedan = retenidos(broker_mqtt, "homeassistant/#")
    assert not set(de_camaras_borradas) & set(quedan)
    assert set(de_la_placa) <= set(quedan), "Los config de la placa no se tocan, aunque su cámara ya no exista."
    assert set(configs_de_la_camara("entrada", "Entrada")) <= set(quedan)
    assert json.loads(quedan[de_una_camara_que_existe]) == configs_de_la_camara("entrada", "Entrada")[de_una_camara_que_existe]
    assert set(configs_del_servidor()) <= set(quedan)
