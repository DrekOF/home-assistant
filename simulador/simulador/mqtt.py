"""
Nombre: mqtt.py
Descripción: La parte MQTT de la cámara en el simulador (contratos/mqtt.md 1.2): disponibilidad con último deseo, la puerta con ABRIR y CERRAR, y EstadoCamara cada 60 s. Solo se crea con --puerta.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Se conecta como la placa del PR #11: el código es el client id y el usuario es camara, que la ACL deja solo en los
temas de su código. La clave sale de la variable MQTT_CAMARA_CLAVE, nunca de una opción.

Usa MQTT 5 para enterarse de que otro cliente se conectó con su código («sesión tomada», 0x8E). Entonces le deja la
puerta y no se reconecta: así la placa siempre se queda con ella. La conexión corre en el hilo de paho y la puerta
en un hilo propio, así que los recortes nunca esperan al broker.
"""

import json
import math
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

import paho.mqtt.client as mqtt
from paho.mqtt.reasoncodes import ReasonCode

from simulador import FIRMWARE
from simulador.consola import numero
from simulador.puerta import CERRADA, SEGUNDOS_POR_DEFECTO, Orden, Puerta, leer_orden

USUARIO = "camara"  # mqtt.md, Broker: lo usan las cámaras y el simulador
VARIABLE_CLAVE = "MQTT_CAMARA_CLAVE"  # el mismo nombre de infra/.env
# 127.0.0.1 y no localhost: en Windows, localhost prueba primero ::1, y la ip de EstadoCamara saldría «::1».
BROKER = "mqtt://127.0.0.1:1883"
PUERTO = 1883
KEEPALIVE_S = 30  # el de la placa
# Reintentos a los 1, 2, 4, 8 y después 10 s, como los envíos sin respuesta (ritmo.py).
ESPERA_MIN_S = 1
ESPERA_MAX_S = 10
PERIODO_ESTADO_S = 60.0  # EstadoCamara cada 60 s (mqtt.md, Temas)
REVISION_S = 0.1  # cada cuánto se mira si la puerta ya debe cerrarse
ESPERA_SALIDA_S = 3.0  # al salir, lo que se espera la confirmación de «cerrada» y «offline»

SESION_TOMADA = 0x8E  # DISCONNECT de MQTT 5: otro cliente se conectó con el mismo client id
# Con estos rechazos del broker no sirve reintentar: no sirven el client id (0x85), el usuario o la clave (0x86),
# o el usuario no tiene permiso (0x87).
RECHAZOS_SIN_REINTENTO = frozenset({0x85, 0x86, 0x87})

# El código va en el client id y en los temas: el patrón de openapi.yaml y de la consola de la placa.
CODIGO = re.compile(r"[a-z0-9-]{3,32}")
CODIGO_RESERVADO = "servidor"  # es el {codigo} de los temas del servidor (mqtt.md, Broker)

FORMA_BROKER = "debe tener la forma mqtt://servidor:puerto, por ejemplo mqtt://192.168.137.1:1883"


def codigo_valido(codigo: str) -> bool:
    return CODIGO.fullmatch(codigo) is not None and codigo != CODIGO_RESERVADO


@dataclass(frozen=True)
class Broker:
    servidor: str
    puerto: int = PUERTO

    def __str__(self) -> str:
        return f"{self.servidor}:{self.puerto}"


def leer_broker(texto: str) -> Broker:
    """mqtt://servidor[:puerto], sin usuario ni clave: la clave va en la variable MQTT_CAMARA_CLAVE.

    Los errores nunca repiten el texto, por si trae una clave.
    """
    partes = urlsplit(texto)
    if partes.scheme != "mqtt" or not partes.netloc:
        raise ValueError(FORMA_BROKER)
    if "@" in partes.netloc:
        raise ValueError(f"no lleva usuario ni clave: la clave va en $env:{VARIABLE_CLAVE}")
    if partes.path not in ("", "/") or partes.query or partes.fragment or not partes.hostname:
        raise ValueError(FORMA_BROKER)
    try:
        puerto = partes.port
    except ValueError:
        raise ValueError(FORMA_BROKER) from None
    if puerto == 0:
        raise ValueError(FORMA_BROKER)
    return Broker(partes.hostname, puerto or PUERTO)


@dataclass(frozen=True)
class Temas:
    """Los temas de la cámara {codigo} que usa el simulador (mqtt.md, Temas)."""

    disponible: str
    estado: str
    puerta_set: str
    puerta_estado: str

    @classmethod
    def de(cls, codigo: str) -> "Temas":
        base = f"accesia/{codigo}"
        return cls(f"{base}/disponible", f"{base}/estado", f"{base}/puerta/set", f"{base}/puerta/estado")


def estado_camara(ip: str | None, segundos_encendida: int) -> str:
    """EstadoCamara del simulador: solo firmware, ip y segundos_encendida (mqtt.md, EstadoCamara).

    Sin perfil, rssi, psram_kb ni libre_kb. firmware es el mismo texto de la cabecera X-AccesIA-Firmware.
    """
    return json.dumps({"firmware": FIRMWARE, "ip": ip, "segundos_encendida": segundos_encendida},
                      separators=(",", ":"))


class ClienteMqtt(Protocol):
    """Lo que el simulador usa de paho.mqtt.client.Client; las pruebas le dan uno falso."""

    on_connect: Any
    on_connect_fail: Any
    on_disconnect: Any
    on_message: Any

    def username_pw_set(self, username: str, password: str) -> None: ...
    def will_set(self, topic: str, payload: str, qos: int, retain: bool) -> None: ...
    def reconnect_delay_set(self, min_delay: int, max_delay: int) -> None: ...
    def connect_async(self, host: str, port: int, keepalive: int) -> None: ...
    def loop_start(self) -> Any: ...
    def loop_stop(self) -> Any: ...
    def subscribe(self, topic: str, qos: int) -> Any: ...
    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> Any: ...
    def disconnect(self) -> Any: ...
    def socket(self) -> Any: ...


def crear_cliente_paho(codigo: str) -> ClienteMqtt:
    """Cliente MQTT 5 con el código como client id: la ACL usa %c para dejarlo solo en sus temas."""
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=codigo, protocol=mqtt.MQTTv5)


def ip_local(cliente: ClienteMqtt) -> str | None:
    """La IP de este lado de la conexión con el broker: 127.0.0.1 si el broker corre en el mismo portátil."""
    try:
        return str(cliente.socket().getsockname()[0])
    except (AttributeError, OSError, IndexError):
        return None


def mostrar(carga: bytes) -> str:
    """Un mensaje recibido, corto y entre comillas, para la consola."""
    texto = repr(carga[:40].decode("utf-8", errors="replace"))
    return texto + ("…" if len(carga) > 40 else "")


class PuertaMqtt:
    """La cámara por MQTT en el simulador: su disponibilidad, su puerta y su EstadoCamara.

    `arrancar` no espera al broker: si no está, paho reintenta solo en su hilo. `cerrar` se llama al salir.
    Cada cambio sale en la consola con la hora; `aviso` le da a la ventana de la webcam el texto de la puerta abierta.
    """

    def __init__(
        self,
        broker: Broker,
        codigo: str,
        clave: str,
        *,
        segundos: int = SEGUNDOS_POR_DEFECTO,
        reloj: Callable[[], float] = time.monotonic,
        salida: Callable[[str], None] = print,
        crear_cliente: Callable[[str], ClienteMqtt] = crear_cliente_paho,
    ) -> None:
        self.broker = broker
        self.codigo = codigo
        self.temas = Temas.de(codigo)
        self._puerta = Puerta(segundos)
        self._reloj = reloj
        self._salida = salida
        self._inicio = reloj()
        self._candado = threading.Lock()
        self._conectada = False
        self._detenida = False  # sesión tomada o rechazo del broker: ya no reintenta
        self._saliendo = False
        self._avisado = False  # ya dijo que no hay conexión: no lo repite en cada reintento
        self._ip: str | None = None
        self._proximo_estado = math.inf
        self._parar = threading.Event()
        self._hilo: threading.Thread | None = None

        self._cliente = crear_cliente(codigo)
        self._cliente.username_pw_set(USUARIO, clave)
        # Último deseo: si el simulador se corta de golpe, el broker publica «offline» por él.
        self._cliente.will_set(self.temas.disponible, "offline", qos=1, retain=True)
        self._cliente.reconnect_delay_set(ESPERA_MIN_S, ESPERA_MAX_S)
        self._cliente.on_connect = self._al_conectar
        self._cliente.on_connect_fail = self._al_fallar
        self._cliente.on_disconnect = self._al_desconectar
        self._cliente.on_message = self._al_recibir

    @property
    def conectada(self) -> bool:
        with self._candado:
            return self._conectada

    @property
    def detenida(self) -> bool:
        """True si otro cliente tomó el código o el broker rechazó la clave: ya no se reconecta."""
        with self._candado:
            return self._detenida

    @property
    def abierta(self) -> bool:
        with self._candado:
            return self._puerta.abierta

    def arrancar(self) -> None:
        """Empieza a conectarse sin esperar: paho se conecta y reintenta en su hilo, y la puerta corre en otro."""
        self._decir(f"Conectando la puerta al broker {self.broker} como {self.codigo}...")
        self._cliente.connect_async(self.broker.servidor, self.broker.puerto, keepalive=KEEPALIVE_S)
        self._cliente.loop_start()
        self._hilo = threading.Thread(target=self._revisar_siempre, name="puerta", daemon=True)
        self._hilo.start()

    def aviso(self) -> str | None:
        """«PUERTA ABIERTA (2 s)» mientras la puerta está abierta, para la ventana de la webcam; si no, None."""
        with self._candado:
            if not self._puerta.abierta:
                return None
            faltan = self._puerta.faltan(self._reloj())
        return f"PUERTA ABIERTA ({max(1, math.ceil(faltan))} s)"

    def revisar(self) -> None:
        """Cierra la puerta si se cumplió su tiempo y publica EstadoCamara cada 60 s. Su hilo la llama cada 0,1 s."""
        with self._candado:
            if self._saliendo:
                return
            ahora = self._reloj()
            cerro = self._puerta.actualizar(ahora)
            if cerro:
                self._publicar(self.temas.puerta_estado, CERRADA, qos=1, retenido=True)
            if self._conectada and ahora >= self._proximo_estado:
                self._publicar_estado(ahora)
        if cerro:
            self._decir("Puerta cerrada")

    def cerrar(self) -> None:
        """Al salir: si la puerta quedó abierta publica «cerrada»; después «offline», y se desconecta.

        Si el simulador se corta de golpe, el broker publica el último deseo («offline»).
        """
        self._parar.set()
        if self._hilo is not None:
            self._hilo.join(1.0)
        with self._candado:
            if self._saliendo:
                return
            self._saliendo = True
            conectada = self._conectada
            cerro = False
            pendientes = []
            if conectada:
                cerro = self._puerta.orden(Orden.CERRAR, self._reloj())
                if cerro:
                    pendientes.append(self._cliente.publish(self.temas.puerta_estado, CERRADA, qos=1, retain=True))
                pendientes.append(self._cliente.publish(self.temas.disponible, "offline", qos=1, retain=True))
        for info in pendientes:
            try:
                info.wait_for_publish(ESPERA_SALIDA_S)
            except (RuntimeError, ValueError):  # se cortó justo ahora: queda el último deseo
                pass
        if cerro:
            self._decir("Puerta cerrada al salir")
        self._cliente.disconnect()
        if conectada:
            # Sin conexión no se espera al hilo de paho: puede estar en medio de un reintento, y el programa ya sale.
            self._cliente.loop_stop()
            self._decir("Puerta desconectada del broker (offline)")

    # --- Lo que llama paho, desde su hilo ---

    def _al_conectar(self, cliente: Any, datos: Any, banderas: Any, codigo: ReasonCode, propiedades: Any) -> None:
        if codigo.is_failure:
            self._al_rechazar(codigo)
            return
        with self._candado:
            if self._saliendo or self._detenida:
                return
            self._conectada = True
            self._avisado = False
            self._ip = ip_local(self._cliente)
            # El mismo orden de la placa: online, la suscripción, la puerta como está y EstadoCamara.
            self._publicar(self.temas.disponible, "online", qos=1, retenido=True)
            self._cliente.subscribe(self.temas.puerta_set, qos=1)
            self._publicar(self.temas.puerta_estado, self._puerta.estado, qos=1, retenido=True)
            self._publicar_estado(self._reloj())
        self._decir(f"Puerta conectada al broker {self.broker} como {self.codigo}: "
                    f"escucha ABRIR y CERRAR en {self.temas.puerta_set}")

    def _al_rechazar(self, codigo: ReasonCode) -> None:
        if codigo.value in RECHAZOS_SIN_REINTENTO:
            self._detener(
                f"El broker no aceptó al usuario {USUARIO} con el código {self.codigo} ({codigo}): revisa "
                f"$env:{VARIABLE_CLAVE} y --codigo. La puerta queda apagada; los recortes siguen."
            )
        else:
            self._sin_conexion(f"El broker no aceptó la conexión ({codigo}): reintento solo; los recortes siguen.")

    def _al_fallar(self, cliente: Any, datos: Any) -> None:
        """No se pudo abrir la conexión (el broker no está o la dirección no es): paho reintenta solo."""
        self._sin_conexion(
            f"Sin conexión con el broker {self.broker}: reintento a los 1, 2, 4, 8 y cada 10 s; los recortes siguen."
        )

    def _al_desconectar(self, cliente: Any, datos: Any, banderas: Any, codigo: ReasonCode, propiedades: Any) -> None:
        with self._candado:
            estaba = self._conectada
            self._conectada = False
            if self._saliendo or self._detenida:
                return
        if codigo == SESION_TOMADA:
            self._detener(
                f"Otro cliente se conectó con el código {self.codigo} (sesión tomada; puede ser la placa): le dejo "
                "la puerta y no me reconecto. Los recortes siguen."
            )
        elif estaba:
            self._sin_conexion(f"Se perdió la conexión con el broker {self.broker}: reintento solo; los recortes siguen.")

    def _al_recibir(self, cliente: Any, datos: Any, mensaje: mqtt.MQTTMessage) -> None:
        if mensaje.topic != self.temas.puerta_set:
            return
        orden = leer_orden(mensaje.payload)
        if orden is None:
            self._decir(f"Mensaje ignorado en {self.temas.puerta_set}: {mostrar(mensaje.payload)} (solo ABRIR o CERRAR)")
            return
        with self._candado:
            if self._saliendo:
                return
            cambia = self._puerta.orden(orden, self._reloj())
            if cambia:
                self._publicar(self.temas.puerta_estado, self._puerta.estado, qos=1, retenido=True)
        segundos = numero(self._puerta.segundos)
        if orden is Orden.ABRIR:
            self._decir(f"PUERTA ABIERTA ({segundos} s)" if cambia
                        else f"ABRIR con la puerta abierta: vuelve a contar {segundos} s")
        else:
            self._decir("Puerta cerrada (CERRAR)" if cambia else "CERRAR con la puerta cerrada: no cambia nada")

    # --- Ayudas ---

    def _publicar(self, tema: str, carga: str, *, qos: int, retenido: bool) -> None:
        """Publica solo con conexión, como la placa.

        Sin conexión, paho guardaría el mensaje y lo enviaría al reconectarse, ya viejo; al reconectarse se publica
        la puerta como esté en ese momento.
        """
        if self._conectada:
            self._cliente.publish(tema, carga, qos=qos, retain=retenido)

    def _publicar_estado(self, ahora: float) -> None:
        self._publicar(self.temas.estado, estado_camara(self._ip, int(ahora - self._inicio)), qos=0, retenido=True)
        self._proximo_estado = ahora + PERIODO_ESTADO_S

    def _detener(self, mensaje: str) -> None:
        """Deja de reintentar: disconnect() saca a paho de su ciclo de reconexión."""
        with self._candado:
            if self._detenida or self._saliendo:
                return
            self._detenida = True
            self._conectada = False
        self._cliente.disconnect()
        self._decir(mensaje)

    def _sin_conexion(self, mensaje: str) -> None:
        with self._candado:
            if self._avisado or self._saliendo or self._detenida:
                return
            self._avisado = True
        self._decir(mensaje)

    def _revisar_siempre(self) -> None:
        while not self._parar.wait(REVISION_S):
            self.revisar()

    def _decir(self, texto: str) -> None:
        self._salida(f"{time.strftime('%H:%M:%S')} {texto}")
