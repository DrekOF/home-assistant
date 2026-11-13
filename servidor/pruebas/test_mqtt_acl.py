"""
Nombre: test_mqtt_acl.py
Descripción: Prueba «contrato MQTT · acl»: Mosquitto con el mosquitto.conf y la ACL del repositorio, comprobados con paho-mqtt. Usa un broker propio, sin los retenidos de las demás pruebas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
"""

import threading
import uuid
from collections.abc import Callable, Iterator

import paho.mqtt.client as mqtt
import pytest
from mqtt_de_prueba import CLAVES, ESPERA_S, broker_de_prueba
from paho.mqtt.reasoncodes import ReasonCode

pytestmark = pytest.mark.marca("contrato MQTT · acl")


@pytest.fixture(scope="module")
def broker() -> Iterator[tuple[str, int]]:
    with broker_de_prueba() as direccion:
        yield direccion


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


def marcar(clientes: Callable[..., Cliente], escucha: Cliente, tema: str = "accesia/prueba/marca") -> None:
    """Publica una marca y espera a que llegue. Mosquitto entrega en orden de llegada:
    si la marca llegó y un mensaje publicado antes no, el broker lo descartó."""
    marcador = clientes(f"prueba-marca-{uuid.uuid4().hex[:8]}", "servidor")
    assert not marcador.conectar().is_failure
    carga = uuid.uuid4().hex
    marcador.publicar(tema, carga)
    assert escucha.esperar(tema, carga), "No llegó la marca."


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


def test_la_placa_publica_su_ambiente_solo_con_su_codigo(clientes: Callable[..., Cliente], escucha: Cliente) -> None:
    """mqtt.md 1.2 (D-21): accesia/{codigo}/ambiente."""
    placa = clientes("entrada", "camara")
    assert not placa.conectar().is_failure
    carga = uuid.uuid4().hex

    placa.publicar("accesia/entrada/ambiente", carga)
    assert escucha.esperar("accesia/entrada/ambiente", carga), "La placa no pudo publicar su ambiente."

    placa.publicar("accesia/otra/ambiente", carga)
    marcar(clientes, escucha)
    assert not escucha.recibio("accesia/otra/ambiente")


@pytest.fixture
def escucha_descubrimiento(clientes: Callable[..., Cliente]) -> Cliente:
    """Suscriptor con el usuario servidor que recibe todo homeassistant/#."""
    suscriptor = clientes(f"prueba-descubrimiento-{uuid.uuid4().hex[:8]}", "servidor")
    assert not suscriptor.conectar().is_failure
    suscriptor.suscribir("homeassistant/#")
    return suscriptor


def test_la_placa_publica_solo_el_descubrimiento_de_sus_dos_sensores(
    clientes: Callable[..., Cliente], escucha_descubrimiento: Cliente
) -> None:
    """mqtt.md 1.2 (D-21): homeassistant/sensor/{codigo}/temperatura/config y …/humedad/config, y nada más."""
    placa = clientes("entrada", "camara")
    assert not placa.conectar().is_failure
    carga = uuid.uuid4().hex

    for objeto in ("temperatura", "humedad"):
        tema = f"homeassistant/sensor/entrada/{objeto}/config"
        placa.publicar(tema, carga)
        assert escucha_descubrimiento.esperar(tema, carga), f"La placa no pudo publicar en {tema}."

    prohibidos = (
        "homeassistant/sensor/otra/temperatura/config",
        "homeassistant/sensor/entrada/otro/config",
        "homeassistant/binary_sensor/entrada/puerta/config",
        "homeassistant/sensor/accesia_entrada/temperatura/config",
    )
    for tema in prohibidos:
        placa.publicar(tema, carga)
    marcar(clientes, escucha_descubrimiento, "homeassistant/prueba/marca")
    for tema in prohibidos:
        assert not escucha_descubrimiento.recibio(tema), f"La placa publicó en {tema}."
