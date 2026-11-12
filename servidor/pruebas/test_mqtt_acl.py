"""
Nombre: test_mqtt_acl.py
Descripción: Prueba «contrato MQTT · acl»: Mosquitto con el mosquitto.conf y la ACL del repositorio, comprobados con paho-mqtt.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

import re
import threading
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.reasoncodes import ReasonCode
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

pytestmark = pytest.mark.marca("contrato MQTT · acl")

MOSQUITTO = Path(__file__).resolve().parents[2] / "infra" / "mosquitto"
CLAVES = {"servidor": "clave-servidor", "homeassistant": "clave-homeassistant", "camara": "clave-camara"}
ESPERA_S = 5


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
def broker() -> Iterator[tuple[str, int]]:
    contenedor = (
        DockerContainer("eclipse-mosquitto:2")
        .with_volume_mapping(str(MOSQUITTO / "mosquitto.conf"), "/mosquitto/config/mosquitto.conf", "ro")
        .with_volume_mapping(str(MOSQUITTO / "acl"), "/mosquitto/config/acl", "ro")
        .with_exposed_ports(1883)
        .with_command(comando_del_broker())
        .waiting_for(LogMessageWaitStrategy(re.compile(r"mosquitto version \S+ running")))
    )
    with contenedor:
        yield contenedor.get_container_host_ip(), int(contenedor.get_exposed_port(1883))


class Cliente:
    """Cliente MQTT 3.1.1 de prueba que guarda los mensajes que recibe."""

    def __init__(self, broker: tuple[str, int], client_id: str, usuario: str | None = None) -> None:
        self._servidor, self._puerto = broker
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv311)
        if usuario is not None:
            self.cliente.username_pw_set(usuario, CLAVES[usuario])
        self.codigo_conexion: ReasonCode | None = None
        self._conectado = threading.Event()
        self._suscrito = threading.Event()
        self._recibidos: list[tuple[str, str]] = []
        self._hay_mensaje = threading.Condition()
        self.cliente.on_connect = self._al_conectar
        self.cliente.on_subscribe = self._al_suscribir
        self.cliente.on_message = self._al_recibir

    def _al_conectar(self, cliente, datos, banderas, codigo: ReasonCode, propiedades) -> None:
        self.codigo_conexion = codigo
        self._conectado.set()

    def _al_suscribir(self, cliente, datos, mid, codigos, propiedades) -> None:
        self._suscrito.set()

    def _al_recibir(self, cliente, datos, mensaje: mqtt.MQTTMessage) -> None:
        with self._hay_mensaje:
            self._recibidos.append((mensaje.topic, mensaje.payload.decode()))
            self._hay_mensaje.notify_all()

    def conectar(self) -> ReasonCode:
        self.cliente.connect(self._servidor, self._puerto, keepalive=10)
        self.cliente.loop_start()
        assert self._conectado.wait(ESPERA_S), "El broker no respondió a la conexión."
        return self.codigo_conexion

    def suscribir(self, tema: str) -> None:
        self.cliente.subscribe(tema, qos=1)
        assert self._suscrito.wait(ESPERA_S), f"El broker no confirmó la suscripción a {tema}."

    def publicar(self, tema: str, carga: str) -> None:
        info = self.cliente.publish(tema, carga, qos=1)
        info.wait_for_publish(timeout=ESPERA_S)
        assert info.is_published(), f"El broker no confirmó la publicación en {tema}."

    def esperar(self, tema: str, carga: str) -> bool:
        with self._hay_mensaje:
            return self._hay_mensaje.wait_for(lambda: (tema, carga) in self._recibidos, timeout=ESPERA_S)

    def recibio(self, tema: str) -> bool:
        with self._hay_mensaje:
            return any(recibido == tema for recibido, _ in self._recibidos)

    def cerrar(self) -> None:
        self.cliente.disconnect()
        self.cliente.loop_stop()


@pytest.fixture
def clientes(broker: tuple[str, int]) -> Iterator[Callable[..., Cliente]]:
    creados: list[Cliente] = []

    def crear(client_id: str, usuario: str | None = None) -> Cliente:
        cliente = Cliente(broker, client_id, usuario)
        creados.append(cliente)
        return cliente

    yield crear
    for cliente in creados:
        cliente.cerrar()


@pytest.fixture
def escucha(clientes: Callable[..., Cliente]) -> Cliente:
    """Suscriptor con el usuario servidor que recibe todo accesia/#."""
    suscriptor = clientes(f"prueba-escucha-{uuid.uuid4().hex[:8]}", "servidor")
    assert not suscriptor.conectar().is_failure
    suscriptor.suscribir("accesia/#")
    return suscriptor


def marcar(clientes: Callable[..., Cliente], escucha: Cliente) -> None:
    """Publica una marca y espera a que llegue. Mosquitto entrega en orden de llegada:
    si la marca llegó y un mensaje publicado antes no, el broker lo descartó."""
    marcador = clientes(f"prueba-marca-{uuid.uuid4().hex[:8]}", "servidor")
    assert not marcador.conectar().is_failure
    carga = uuid.uuid4().hex
    marcador.publicar("accesia/prueba/marca", carga)
    assert escucha.esperar("accesia/prueba/marca", carga), "No llegó la marca."


def test_una_conexion_anonima_es_rechazada(clientes: Callable[..., Cliente]) -> None:
    anonimo = clientes(f"prueba-anonimo-{uuid.uuid4().hex[:8]}")

    assert anonimo.conectar().is_failure


@pytest.mark.parametrize("usuario", list(CLAVES))
def test_los_usuarios_del_contrato_entran(clientes: Callable[..., Cliente], usuario: str) -> None:
    assert not clientes(f"prueba-{usuario}-{uuid.uuid4().hex[:8]}", usuario).conectar().is_failure


def test_la_camara_con_client_id_servidor_no_publica_por_el_servidor(
    clientes: Callable[..., Cliente], escucha: Cliente
) -> None:
    impostor = clientes("servidor", "camara")
    assert not impostor.conectar().is_failure

    impostor.publicar("accesia/servidor/disponible", "offline")
    marcar(clientes, escucha)

    assert not escucha.recibio("accesia/servidor/disponible")


def test_la_camara_publica_solo_en_los_temas_de_su_client_id(
    clientes: Callable[..., Cliente], escucha: Cliente
) -> None:
    camara = clientes("entrada", "camara")
    assert not camara.conectar().is_failure
    carga = uuid.uuid4().hex

    camara.publicar("accesia/entrada/estado", carga)
    assert escucha.esperar("accesia/entrada/estado", carga), "La cámara no pudo publicar en su propio tema."

    camara.publicar("accesia/otra/estado", carga)
    marcar(clientes, escucha)
    assert not escucha.recibio("accesia/otra/estado")
