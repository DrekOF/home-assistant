"""
Nombre: mqtt_de_prueba.py
Descripción: Mosquitto de prueba con el mosquitto.conf y la ACL del repositorio, un cliente que guarda tema, carga, QoS y retención de cada mensaje que recibe, y la limpieza de los mensajes retenidos entre pruebas.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import json
import re
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import paho.mqtt.client as mqtt
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

MOSQUITTO = Path(__file__).resolve().parents[2] / "infra" / "mosquitto"
CLAVES = {"servidor": "clave-servidor", "homeassistant": "clave-homeassistant", "camara": "clave-camara"}
ESPERA_S = 5

Direccion = tuple[str, int]


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


@contextmanager
def broker_de_prueba() -> Iterator[Direccion]:
    """Un Mosquitto 2 en un contenedor, con el mosquitto.conf y la ACL del repositorio."""
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


def url_del_servidor(broker: Direccion) -> str:
    """MQTT_URL del usuario servidor, como la arma Docker Compose."""
    servidor, puerto = broker
    return f"mqtt://servidor:{CLAVES['servidor']}@{servidor}:{puerto}"


@dataclass(frozen=True)
class Mensaje:
    tema: str
    carga: str
    qos: int
    retenido: bool

    def json(self) -> object:
        return json.loads(self.carga)


class ClienteDePrueba:
    """Cliente MQTT 3.1.1 que guarda todo lo que recibe.

    Se suscribe con QoS 2: el broker entrega cada mensaje con la QoS menor entre la de la suscripción y la de la
    publicación, así que la QoS que llega es la que usó quien publicó. retenido es True solo en los mensajes
    retenidos que el broker entrega al suscribirse; los que se reenvían en vivo llegan con retenido False.
    """

    def __init__(self, broker: Direccion, usuario: str, client_id: str | None = None) -> None:
        self._broker = broker
        identificador = client_id or f"prueba-{usuario}-{uuid.uuid4().hex[:8]}"
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=identificador, protocol=mqtt.MQTTv311)
        self.cliente.username_pw_set(usuario, CLAVES[usuario])
        self._conectado = threading.Event()
        self._suscrito = threading.Event()
        self._mensajes: list[Mensaje] = []
        self._hay_mensaje = threading.Condition()
        self.cliente.on_connect = lambda *_: self._conectado.set()
        self.cliente.on_subscribe = lambda *_: self._suscrito.set()
        self.cliente.on_message = self._al_recibir

    def _al_recibir(self, _cliente, _datos, mensaje: mqtt.MQTTMessage) -> None:
        recibido = Mensaje(mensaje.topic, mensaje.payload.decode("utf-8"), mensaje.qos, bool(mensaje.retain))
        with self._hay_mensaje:
            self._mensajes.append(recibido)
            self._hay_mensaje.notify_all()

    def conectar(self) -> "ClienteDePrueba":
        self.cliente.connect(*self._broker, keepalive=10)
        self.cliente.loop_start()
        assert self._conectado.wait(ESPERA_S), "El broker no respondió a la conexión."
        return self

    def suscribir(self, *temas: str) -> None:
        self._suscrito.clear()
        self.cliente.subscribe([(tema, 2) for tema in temas])
        assert self._suscrito.wait(ESPERA_S), f"El broker no confirmó la suscripción a {temas}."

    def publicar(self, tema: str, carga: str = "", retenido: bool = False, qos: int = 1) -> None:
        info = self.cliente.publish(tema, carga, qos=qos, retain=retenido)
        info.wait_for_publish(timeout=ESPERA_S)
        assert info.is_published(), f"El broker no confirmó la publicación en {tema}."

    def mensajes(self, tema: str | None = None) -> list[Mensaje]:
        with self._hay_mensaje:
            return [mensaje for mensaje in self._mensajes if tema is None or mensaje.tema == tema]

    def esperar(
        self, tema: str, condicion: Callable[[Mensaje], bool] = lambda _: True, espera_s: float = ESPERA_S
    ) -> Mensaje:
        """El primer mensaje de ese tema que cumple la condición; espera hasta que llegue."""

        def buscar() -> Mensaje | None:
            return next((m for m in self._mensajes if m.tema == tema and condicion(m)), None)

        with self._hay_mensaje:
            assert self._hay_mensaje.wait_for(lambda: buscar() is not None, timeout=espera_s), f"No llegó en {tema}."
            encontrado = buscar()
        assert encontrado is not None
        return encontrado

    def olvidar(self) -> None:
        with self._hay_mensaje:
            self._mensajes.clear()

    def cerrar(self) -> None:
        self.cliente.disconnect()
        self.cliente.loop_stop()


def retenidos(broker: Direccion, *temas: str) -> dict[str, str]:
    """Los mensajes retenidos que guarda el broker en esos temas. Los entrega al suscribirse, antes que la marca que
    se publica después: cuando llega la marca, ya llegaron todos."""
    lector = ClienteDePrueba(broker, "servidor").conectar()
    try:
        marca = f"accesia/prueba/marca-{uuid.uuid4().hex[:8]}"
        lector.suscribir(*temas, marca)
        lector.publicar(marca, "fin")
        lector.esperar(marca)
        return {mensaje.tema: mensaje.carga for mensaje in lector.mensajes() if mensaje.retenido}
    finally:
        lector.cerrar()


def limpiar_retenidos(broker: Direccion) -> None:
    """Borra, con un mensaje vacío retenido, todo lo retenido en accesia/# y homeassistant/#."""
    temas = retenidos(broker, "accesia/#", "homeassistant/#")
    if not temas:
        return
    limpiador = ClienteDePrueba(broker, "servidor").conectar()
    try:
        for tema in temas:
            limpiador.publicar(tema, "", retenido=True)
    finally:
        limpiador.cerrar()


def hasta(condicion: Callable[[], bool], espera_s: float = ESPERA_S, intervalo_s: float = 0.02) -> bool:
    """Vuelve a mirar la condición hasta que se cumpla o pase la espera. Sirve para lo que el servidor procesa en su
    propio hilo, como la disponibilidad y el estado de una cámara."""
    limite = time.monotonic() + espera_s
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(intervalo_s)
    return condicion()
