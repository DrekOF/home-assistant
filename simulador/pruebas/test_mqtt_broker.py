"""
Nombre: test_mqtt_broker.py
Descripción: La puerta del simulador contra Mosquitto de verdad, con el mosquitto.conf y la ACL del repositorio (como test_mqtt_acl.py del servidor): online y el último deseo, ABRIR y CERRAR desde homeassistant, los retenidos, EstadoCamara y la sesión tomada por la placa.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Necesita Docker: levanta su propio Mosquitto en un puerto libre, aparte del compose. Sin Docker se salta; en la CI
(CI=true) falla, para que nunca pase sin probar.
"""

import ipaddress
import json
import os
import re
import socket
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.subscribeoptions import SubscribeOptions

from simulador import FIRMWARE
from simulador.mqtt import Broker, ClienteMqtt, PuertaMqtt, crear_cliente_paho
from simulador.rutas import RAIZ

MOSQUITTO = RAIZ / "infra" / "mosquitto"
CLAVES = {"servidor": "clave-servidor", "homeassistant": "clave-homeassistant", "camara": "clave-camara"}
ESPERA_S = 10


def _hay_docker() -> bool:
    try:
        import docker

        docker.from_env().ping()
    except Exception:  # noqa: BLE001 — sin Docker Desktop, sin permisos o sin la librería: no hay Docker
        return False
    return True


def comando_del_broker() -> list[str]:
    """Crea las claves de prueba dentro del contenedor y arranca Mosquitto con la configuración del repositorio."""
    archivo = "/mosquitto/config/claves/passwd"
    pasos = ["mkdir -p /mosquitto/config/claves"]
    for indice, (usuario, clave) in enumerate(CLAVES.items()):
        crear = "-c " if indice == 0 else ""
        pasos.append(f"mosquitto_passwd -b {crear}{archivo} {usuario} {clave}")
    pasos += [
        f"chown mosquitto:mosquitto {archivo}",
        f"chmod 0700 {archivo}",
        "exec mosquitto -c /mosquitto/config/mosquitto.conf",
    ]
    return ["sh", "-c", " && ".join(pasos)]


@pytest.fixture(scope="module")
def broker() -> Iterator[Broker]:
    if not _hay_docker():
        if os.environ.get("CI"):
            pytest.fail("En la CI la puerta se prueba contra Mosquitto de verdad: falta Docker.")
        pytest.skip("Sin Docker: la puerta contra Mosquitto de verdad se prueba en la CI.")
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    contenedor = (
        DockerContainer("eclipse-mosquitto:2")
        .with_volume_mapping(str(MOSQUITTO / "mosquitto.conf"), "/mosquitto/config/mosquitto.conf", "ro")
        .with_volume_mapping(str(MOSQUITTO / "acl"), "/mosquitto/config/acl", "ro")
        .with_exposed_ports(1883)
        .with_command(comando_del_broker())
        .waiting_for(LogMessageWaitStrategy(re.compile(r"mosquitto version \S+ running")))
    )
    with contenedor:
        servidor = contenedor.get_container_host_ip()
        # «localhost» puede probar primero ::1; en Windows, cada intento rechazado tarda unos 2 s.
        yield Broker("127.0.0.1" if servidor == "localhost" else servidor, int(contenedor.get_exposed_port(1883)))


@dataclass(frozen=True)
class Recibido:
    tema: str
    carga: str
    qos: int
    retenido: bool


class Cliente:
    """Un cliente MQTT de prueba (servidor, homeassistant o la placa) que guarda lo que recibe."""

    def __init__(self, broker: Broker, usuario: str, *, client_id: str | None = None,
                 protocolo: int = mqtt.MQTTv5) -> None:
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                   client_id=client_id or f"prueba-{usuario}-{uuid.uuid4().hex[:8]}",
                                   protocol=protocolo)
        self.cliente.username_pw_set(usuario, CLAVES[usuario])
        self._broker = broker
        self.recibidos: list[Recibido] = []
        self._hay = threading.Condition()
        self._conectado = threading.Event()
        self._suscrito = threading.Event()
        self.desconectado = threading.Event()
        self.al_conectar: Callable[[], None] | None = None
        self.cliente.on_connect = self._al_conectar
        self.cliente.on_subscribe = lambda *_: self._suscrito.set()
        self.cliente.on_message = self._al_recibir
        self.cliente.on_disconnect = lambda *_: self.desconectado.set()

    def _al_conectar(self, cliente: mqtt.Client, datos: object, banderas: object, codigo: object,
                     propiedades: object) -> None:
        if self.al_conectar is not None:
            self.al_conectar()
        self._conectado.set()

    def _al_recibir(self, cliente: mqtt.Client, datos: object, mensaje: mqtt.MQTTMessage) -> None:
        with self._hay:
            self.recibidos.append(Recibido(mensaje.topic, mensaje.payload.decode(), mensaje.qos, bool(mensaje.retain)))
            self._hay.notify_all()

    def conectar(self) -> "Cliente":
        self.cliente.connect(self._broker.servidor, self._broker.puerto, keepalive=10)
        self.cliente.loop_start()
        assert self._conectado.wait(ESPERA_S), "El broker no respondió a la conexión."
        return self

    def suscribir(self, tema: str) -> "Cliente":
        """Con QoS 2 y «retain as published»: cada mensaje llega con la QoS y el retenido con que se publicó."""
        self.cliente.subscribe(tema, options=SubscribeOptions(qos=2, retainAsPublished=True))
        assert self._suscrito.wait(ESPERA_S), f"El broker no confirmó la suscripción a {tema}."
        return self

    def publicar(self, tema: str, carga: str, *, retenido: bool = False) -> None:
        info = self.cliente.publish(tema, carga, qos=1, retain=retenido)
        info.wait_for_publish(timeout=ESPERA_S)
        assert info.is_published(), f"El broker no confirmó la publicación en {tema}."

    def esperar(self, condicion: Callable[[list[Recibido]], bool], segundos: float = ESPERA_S) -> bool:
        with self._hay:
            return self._hay.wait_for(lambda: condicion(self.recibidos), timeout=segundos)

    def en(self, tema: str) -> list[Recibido]:
        with self._hay:
            return [recibido for recibido in self.recibidos if recibido.tema == tema]

    def cerrar(self) -> None:
        self.cliente.disconnect()
        self.cliente.loop_stop()


@dataclass
class Camara:
    """La puerta del simulador con un código nuevo, y quien escucha sus temas con el usuario servidor."""

    codigo: str
    puerta: PuertaMqtt
    escucha: Cliente
    lineas: list[str]
    paho: ClienteMqtt

    def tema(self, sufijo: str) -> str:
        return f"accesia/{self.codigo}/{sufijo}"

    def recibido(self, sufijo: str, carga: str, qos: int = 1, retenido: bool = True) -> Recibido:
        return Recibido(self.tema(sufijo), carga, qos, retenido)

    def cargas(self, sufijo: str) -> list[str]:
        return [recibido.carga for recibido in self.escucha.en(self.tema(sufijo))]


class Escenario:
    """Crea cámaras del simulador y clientes de prueba contra el broker, y los cierra al terminar la prueba."""

    def __init__(self, broker: Broker) -> None:
        self.broker = broker
        self._camaras: list[Camara] = []
        self._clientes: list[Cliente] = []

    def cliente(self, usuario: str, *, client_id: str | None = None, protocolo: int = mqtt.MQTTv5) -> Cliente:
        cliente = Cliente(self.broker, usuario, client_id=client_id, protocolo=protocolo)
        self._clientes.append(cliente)
        return cliente

    def camara(self, segundos: int = 3) -> Camara:
        codigo = f"sim-{uuid.uuid4().hex[:8]}"  # un código nuevo por prueba: sin retenidos de otras
        escucha = self.cliente("servidor").conectar().suscribir(f"accesia/{codigo}/#")
        lineas: list[str] = []
        creados: list[ClienteMqtt] = []

        def crear_cliente(client_id: str) -> ClienteMqtt:
            creados.append(crear_cliente_paho(client_id))
            return creados[-1]

        puerta = PuertaMqtt(self.broker, codigo, CLAVES["camara"], segundos=segundos, salida=lineas.append,
                            crear_cliente=crear_cliente)
        camara = Camara(codigo, puerta, escucha, lineas, creados[0])
        self._camaras.append(camara)
        puerta.arrancar()
        assert escucha.esperar(lambda recibidos: camara.recibido("disponible", "online") in recibidos), (
            "El simulador no publicó online."
        )
        return camara

    def cerrar(self) -> None:
        for camara in self._camaras:
            camara.puerta.cerrar()
        for cliente in self._clientes:
            cliente.cerrar()


@pytest.fixture
def escenario(broker: Broker) -> Iterator[Escenario]:
    escenario = Escenario(broker)
    yield escenario
    escenario.cerrar()


@pytest.mark.marca("contrato MQTT · disponible")
def test_online_al_conectarse_offline_al_salir(escenario: Escenario) -> None:
    camara = escenario.camara()
    assert camara.escucha.esperar(lambda recibidos: camara.recibido("puerta/estado", "cerrada") in recibidos)

    camara.puerta.cerrar()

    assert camara.escucha.esperar(lambda _: camara.cargas("disponible") == ["online", "offline"])
    assert camara.escucha.en(camara.tema("disponible"))[-1] == camara.recibido("disponible", "offline")


@pytest.mark.marca("contrato MQTT · disponible")
def test_si_se_corta_de_golpe_queda_el_ultimo_deseo_y_se_reconecta(escenario: Escenario) -> None:
    camara = escenario.camara()

    camara.paho.socket().shutdown(socket.SHUT_RDWR)  # sin DISCONNECT: el broker publica el último deseo

    assert camara.escucha.esperar(lambda _: camara.cargas("disponible") == ["online", "offline", "online"]), (
        "Faltó el último deseo o la reconexión."
    )
    assert all(r.qos == 1 and r.retenido for r in camara.escucha.en(camara.tema("disponible")))


@pytest.mark.marca("contrato MQTT · puerta")
def test_abrir_de_home_assistant_abre_y_cierra_la_puerta(escenario: Escenario) -> None:
    camara = escenario.camara(segundos=1)
    ha = escenario.cliente("homeassistant", protocolo=mqtt.MQTTv311).conectar()

    ha.publicar(camara.tema("puerta/set"), "ABRIR")

    assert camara.escucha.esperar(lambda recibidos: camara.recibido("puerta/estado", "abierta") in recibidos)
    abierta = time.monotonic()
    assert camara.escucha.esperar(lambda _: camara.cargas("puerta/estado") == ["cerrada", "abierta", "cerrada"])
    assert 0.5 <= time.monotonic() - abierta <= 3
    assert all(r.qos == 1 and r.retenido for r in camara.escucha.en(camara.tema("puerta/estado")))
    assert any("PUERTA ABIERTA (1 s)" in linea for linea in camara.lineas)


@pytest.mark.marca("contrato MQTT · puerta")
def test_cerrar_de_home_assistant_la_cierra_antes(escenario: Escenario) -> None:
    camara = escenario.camara(segundos=30)
    ha = escenario.cliente("homeassistant", protocolo=mqtt.MQTTv311).conectar()
    ha.publicar(camara.tema("puerta/set"), "ABRIR")
    assert camara.escucha.esperar(lambda recibidos: camara.recibido("puerta/estado", "abierta") in recibidos)

    ha.publicar(camara.tema("puerta/set"), "CERRAR")

    assert camara.escucha.esperar(lambda _: camara.cargas("puerta/estado") == ["cerrada", "abierta", "cerrada"],
                                  segundos=5)


@pytest.mark.marca("contrato MQTT · estado del simulador")
def test_estado_retenido_con_qos_0_y_solo_tres_campos(escenario: Escenario) -> None:
    camara = escenario.camara()

    assert camara.escucha.esperar(lambda recibidos: any(r.tema == camara.tema("estado") for r in recibidos))
    [estado] = camara.escucha.en(camara.tema("estado"))
    assert (estado.qos, estado.retenido) == (0, True)
    cuerpo = json.loads(estado.carga)
    assert set(cuerpo) == {"firmware", "ip", "segundos_encendida"}
    assert cuerpo["firmware"] == FIRMWARE
    ipaddress.ip_address(cuerpo["ip"])
    assert isinstance(cuerpo["segundos_encendida"], int) and cuerpo["segundos_encendida"] >= 0


@pytest.mark.marca("contrato MQTT · broker")
def test_si_la_placa_toma_el_codigo_el_simulador_le_deja_la_puerta(escenario: Escenario) -> None:
    camara = escenario.camara()
    # La placa: MQTT 3.1.1, el mismo client id y el usuario camara, con su último deseo y su online.
    placa = escenario.cliente("camara", client_id=camara.codigo, protocolo=mqtt.MQTTv311)
    placa.cliente.will_set(camara.tema("disponible"), "offline", qos=1, retain=True)
    placa.al_conectar = lambda: placa.cliente.publish(camara.tema("disponible"), "online", qos=1, retain=True)

    placa.conectar()

    limite = time.monotonic() + ESPERA_S
    while not camara.puerta.detenida and time.monotonic() < limite:
        time.sleep(0.05)
    assert camara.puerta.detenida, "El simulador no se enteró de que la placa tomó su código."
    assert any("sesión tomada" in linea for linea in camara.lineas)
    # Pasan más que los primeros reintentos (1 y 2 s): el simulador no vuelve y la placa sigue conectada.
    time.sleep(4)
    assert not placa.desconectado.is_set(), "El simulador volvió a conectarse y sacó a la placa."
    assert not camara.puerta.conectada
    # El broker publica el último deseo del simulador al darle el código a la placa, antes del online de ella:
    # lo que queda retenido es el online de la placa.
    assert camara.cargas("disponible") == ["online", "offline", "online"]
