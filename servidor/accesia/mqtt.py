"""
Nombre: mqtt.py
Descripción: El servidor en MQTT (mqtt.md 1.3): su conexión con último deseo y reconexión sola; el Evento, la Alerta, el Resumen y el descubrimiento, que se publican solo con conexión; la limpieza del descubrimiento de cámaras que ya no existen, y la disponibilidad y el estado de las cámaras.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import asyncio
import json
import logging
import re
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import unquote, urlsplit

import paho.mqtt.client as mqtt
from fastapi import Depends, Request
from pydantic import ValidationError
from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from accesia import __version__, descubrimiento
from accesia.asistencia import Llegada
from accesia.db import transaccion
from accesia.esquemas import EstadoCamara, RespuestaRostro
from accesia.resumen import resumen
from accesia.tiempo import a_colombia, ahora

registro = logging.getLogger(__name__)

# El código servidor está reservado: ninguna cámara puede usarlo como client id y sacar al servidor del broker.
CLIENT_ID = "servidor"
KEEPALIVE_S = 30
INTERVALO_RESUMEN_S = 300  # mqtt.md: el resumen también sale cada 5 minutos, así cambia de día a medianoche

TEMA_DISPONIBLE = "accesia/servidor/disponible"
TEMA_RESUMEN = "accesia/resumen"
TEMA_ESTADO_HOME_ASSISTANT = "homeassistant/status"
SUSCRIPCIONES = [
    (TEMA_ESTADO_HOME_ASSISTANT, 1),
    ("accesia/+/disponible", 1),
    ("accesia/+/estado", 1),
    # Para la limpieza: al suscribirse, el broker entrega los config retenidos de todos los dispositivos.
    ("homeassistant/+/+/+/config", 1),
]

_CODIGO = re.compile(r"^[a-z0-9-]{3,32}$")

AbrirConexion = Callable[[], AbstractContextManager[Connection]]


@dataclass(frozen=True)
class Publicacion:
    tema: str
    carga: str
    qos: int
    retenido: bool


@dataclass(frozen=True)
class Pendiente:
    """Lo que publica un recorte después de confirmar su transacción: el evento, la alerta de R6 y el resumen."""

    codigo: str
    evento: dict | None = None
    alerta: dict | None = None
    resumen: bool = False


def json_de(datos: object) -> str:
    return json.dumps(datos, ensure_ascii=False)


def mensaje_evento(codigo: str, respuesta: RespuestaRostro, llegada: Llegada | None) -> dict:
    """El Evento de mqtt.md. asistencia solo va si este evento creó la llegada del día. En una repetición de R4,
    evento_id es el del original y la persona, la similitud y la hora son las de este recorte. Un desconocido no
    lleva persona: nunca se publica a quién se parece (RNF-01 · C3)."""
    persona = respuesta.persona
    return {
        "evento_id": str(respuesta.evento_id),
        "dispositivo": codigo,
        "resultado": respuesta.resultado,
        "motivo": respuesta.motivo,
        "persona": None if persona is None else {"id": str(persona.id), "nombre": persona.nombre},
        "similitud": respuesta.similitud,
        "repetido": respuesta.repetido,
        "asistencia": None if llegada is None else {"estado": llegada.estado, "minutos_tarde": llegada.minutos_tarde},
        "hora": a_colombia(respuesta.hora).isoformat(),
    }


def estado_de_camara(carga: bytes) -> EstadoCamara | None:
    """El EstadoCamara de mqtt.md, o None si no cumple: no es un objeto JSON, trae null o un tipo que no es el suyo."""
    try:
        datos = json.loads(carga)
    except ValueError:
        return None
    if not isinstance(datos, dict) or any(valor is None for valor in datos.values()):
        return None
    try:
        return EstadoCamara.model_validate(datos, strict=True)
    except ValidationError:
        return None


def _usuario_y_clave(partes) -> tuple[str, str] | None:
    if not partes.username:
        return None
    return unquote(partes.username), unquote(partes.password or "")


@dataclass
class _Camara:
    disponible: bool | None = None
    estado: EstadoCamara | None = None


class ClienteMqtt:
    """La conexión del servidor con el broker. Sin url (pruebas, PC sin broker) no se conecta ni publica nada."""

    def __init__(
        self,
        url: str | None,
        conexiones: AbrirConexion = transaccion,
        client_id: str = CLIENT_ID,
        version: str = __version__,
    ) -> None:
        self._conexiones = conexiones
        self._version = version
        self._camaras: dict[str, _Camara] = {}
        self._candado = threading.Lock()
        self._listo = threading.Event()
        self._fallo_avisado = False
        self._trabajo: ThreadPoolExecutor | None = None
        self._cliente: mqtt.Client | None = None
        if url is None:
            return
        partes = urlsplit(url)
        self._servidor = partes.hostname or "localhost"
        self._puerto = partes.port or 1883
        self._client_id = client_id
        cliente = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=True, protocol=mqtt.MQTTv311
        )
        if (credenciales := _usuario_y_clave(partes)) is not None:
            cliente.username_pw_set(*credenciales)
        cliente.will_set(TEMA_DISPONIBLE, "offline", qos=1, retain=True)
        cliente.reconnect_delay_set(min_delay=1, max_delay=30)
        cliente.on_connect = self._al_conectar
        cliente.on_connect_fail = self._al_fallar
        cliente.on_disconnect = self._al_desconectar
        cliente.on_message = self._al_recibir
        self._cliente = cliente

    # --- Ciclo de vida ---

    @property
    def habilitado(self) -> bool:
        return self._cliente is not None

    @property
    def conectado(self) -> bool:
        return self._cliente is not None and self._cliente.is_connected()

    def iniciar(self) -> None:
        """Se conecta sin esperar al broker: si no responde, el servidor arranca igual y paho reintenta solo."""
        if self._cliente is None:
            registro.info("MQTT: sin MQTT_URL, el servidor no publica en MQTT.")
            return
        self._trabajo = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mqtt")
        self._cliente.connect_async(self._servidor, self._puerto, keepalive=KEEPALIVE_S)
        self._cliente.loop_start()

    def detener(self) -> None:
        """Al apagarse publica offline (un cierre ordenado no dispara el último deseo) y se desconecta."""
        if self._cliente is None:
            return
        if self.conectado:
            try:
                self._cliente.publish(TEMA_DISPONIBLE, "offline", qos=1, retain=True).wait_for_publish(timeout=2)
            except (ValueError, RuntimeError):
                pass
            self._cliente.disconnect()
        self._cliente.loop_stop()
        if self._trabajo is not None:
            self._trabajo.shutdown(wait=True, cancel_futures=True)
            self._trabajo = None

    def esperar_listo(self, espera_s: float) -> bool:
        """True cuando terminó lo que hace al conectarse: el descubrimiento y el resumen."""
        return self._listo.wait(espera_s)

    def esperar_trabajo(self, espera_s: float) -> bool:
        """True cuando el hilo de trabajo terminó lo que tenía en cola, como la limpieza (lo usan las pruebas)."""
        if self._trabajo is None:
            return True
        try:
            self._trabajo.submit(lambda: None).result(timeout=espera_s)
        except TimeoutError:
            return False
        return True

    # --- Publicar ---

    def publicar(self, publicacion: Publicacion) -> bool:
        """Publica solo con conexión. Sin ella descarta el mensaje: paho lo guardaría y lo mandaría al reconectar, y un
        permitido viejo abriría la puerta tarde. Lo retenido se vuelve a publicar al reconectar."""
        if not self.conectado:
            if self.habilitado:
                registro.warning("MQTT: sin conexión con el broker, no se publica en %s.", publicacion.tema)
            return False
        assert self._cliente is not None
        info = self._cliente.publish(
            publicacion.tema, publicacion.carga, qos=publicacion.qos, retain=publicacion.retenido
        )
        return info.rc == mqtt.MQTT_ERR_SUCCESS

    def publicar_recorte(self, pendiente: Pendiente) -> None:
        """Corre como tarea de fondo, después de confirmar la transacción del recorte y de enviar la respuesta.
        Primero el evento, que abre la puerta; después la alerta y el resumen."""
        if pendiente.evento is not None:
            self.publicar(Publicacion(f"accesia/{pendiente.codigo}/evento", json_de(pendiente.evento), 1, False))
        if pendiente.alerta is not None:
            self.publicar(Publicacion(f"accesia/{pendiente.codigo}/alerta", json_de(pendiente.alerta), 1, False))
        if pendiente.resumen:
            self.publicar_resumen()

    def publicar_resumen(self) -> None:
        if not self.conectado:
            return
        try:
            with self._conexiones() as conexion:
                datos = resumen(conexion, ahora())
        except SQLAlchemyError:
            registro.exception("MQTT: no se pudo armar el resumen: la base no respondió.")
            return
        self.publicar(Publicacion(TEMA_RESUMEN, json_de(datos), 1, True))

    def publicar_descubrimiento(self, codigo: str | None = None) -> None:
        """Los config del servidor y de todas las cámaras; con un código, solo los de esa cámara."""
        if not self.conectado:
            return
        consulta = "SELECT codigo, nombre FROM dispositivo"
        if codigo is not None:
            consulta += " WHERE codigo = :codigo"
        try:
            with self._conexiones() as conexion:
                camaras = conexion.execute(text(consulta + " ORDER BY codigo"), {"codigo": codigo}).all()
        except SQLAlchemyError:
            registro.exception("MQTT: no se pudo leer las cámaras para el descubrimiento: la base no respondió.")
            return
        configs = [] if codigo is not None else descubrimiento.configs_del_servidor(self._version)
        for camara in camaras:
            configs += descubrimiento.configs_de_camara(camara.codigo, camara.nombre, self._version)
        for tema, datos in configs:
            self.publicar(Publicacion(tema, json_de(datos), 1, True))

    # --- Cámaras: lo que publican en MQTT ---

    def en_linea(self, codigo: str) -> bool:
        """online en MQTT, mientras el servidor siga conectado al broker (sin conexión no se sabe)."""
        if not self.conectado:
            return False
        with self._candado:
            camara = self._camaras.get(codigo)
            return camara is not None and camara.disponible is True

    def estado(self, codigo: str) -> EstadoCamara | None:
        """El último EstadoCamara válido que publicó la cámara; se conserva aunque se pierda el broker."""
        with self._candado:
            camara = self._camaras.get(codigo)
            return None if camara is None else camara.estado

    # --- Lo que llega del broker (hilo de paho: lo que usa la base pasa al hilo de trabajo) ---

    def _al_conectar(self, cliente: mqtt.Client, _datos, _banderas, codigo, _propiedades) -> None:
        if codigo.is_failure:
            registro.warning("MQTT: el broker rechazó la conexión (%s); reintenta solo.", codigo)
            return
        self._fallo_avisado = False
        registro.info("MQTT: conectado a %s:%s como %s.", self._servidor, self._puerto, self._client_id)
        cliente.publish(TEMA_DISPONIBLE, "online", qos=1, retain=True)
        cliente.subscribe(SUSCRIPCIONES)
        if self._trabajo is not None:
            self._trabajo.submit(self._al_conectar_en_el_trabajo)

    def _al_conectar_en_el_trabajo(self) -> None:
        self.publicar_descubrimiento()
        self.publicar_resumen()
        self._listo.set()

    def _al_fallar(self, _cliente, _datos) -> None:
        if not self._fallo_avisado:
            self._fallo_avisado = True
            registro.warning("MQTT: no se pudo conectar con %s:%s; reintenta solo.", self._servidor, self._puerto)

    def _al_desconectar(self, _cliente, _datos, _banderas, codigo, _propiedades) -> None:
        self._listo.clear()
        if codigo.is_failure:
            registro.warning("MQTT: se perdió la conexión con el broker (%s); reintenta solo.", codigo)

    def _al_recibir(self, _cliente, _datos, mensaje: mqtt.MQTTMessage) -> None:
        partes = mensaje.topic.split("/")
        if mensaje.topic == TEMA_ESTADO_HOME_ASSISTANT:
            # Home Assistant volvió: se le vuelve a publicar el descubrimiento. Un online retenido llega al conectarse,
            # cuando el servidor ya lo publica.
            if mensaje.payload == b"online" and not mensaje.retain:
                self._en_el_trabajo(self.publicar_descubrimiento)
        elif partes[0] == "accesia" and len(partes) == 3 and partes[1] != "servidor" and _CODIGO.match(partes[1]):
            if partes[2] == "disponible":
                self._guardar_disponible(partes[1], mensaje.payload)
            elif partes[2] == "estado":
                self._guardar_estado(partes[1], mensaje.payload)
        elif mensaje.retain and mensaje.payload:
            codigo = descubrimiento.codigo_de_config(mensaje.topic)
            if codigo is not None:
                self._en_el_trabajo(self._limpiar, mensaje.topic, codigo)

    def _en_el_trabajo(self, funcion: Callable, *argumentos) -> None:
        if self._trabajo is not None:
            self._trabajo.submit(funcion, *argumentos)

    def _guardar_disponible(self, codigo: str, carga: bytes) -> None:
        if carga not in (b"online", b"offline", b""):
            registro.warning("MQTT: descarto la disponibilidad de %s: no es online ni offline.", codigo)
            return
        with self._candado:
            self._camaras.setdefault(codigo, _Camara()).disponible = None if not carga else carga == b"online"

    def _guardar_estado(self, codigo: str, carga: bytes) -> None:
        estado = None
        if carga:  # vacío: se borró el retenido y ya no hay estado
            estado = estado_de_camara(carga)
            if estado is None:
                registro.warning("MQTT: descarto el estado de %s: no cumple EstadoCamara.", codigo)
                return
        with self._candado:
            self._camaras.setdefault(codigo, _Camara()).estado = estado

    def _limpiar(self, tema: str, codigo: str) -> None:
        """Borra el config retenido de una cámara que ya no existe, con un mensaje vacío retenido. Solo llegan aquí
        los del servidor (nodo accesia_{codigo}): los de la placa nunca se tocan."""
        try:
            with self._conexiones() as conexion:
                existe = conexion.execute(
                    text("SELECT 1 FROM dispositivo WHERE codigo = :codigo"), {"codigo": codigo}
                ).first()
        except SQLAlchemyError:
            registro.exception("MQTT: no se pudo revisar la cámara %s para la limpieza.", codigo)
            return
        if existe is None:
            registro.info("MQTT: borro %s, de la cámara %s, que ya no existe.", tema, codigo)
            self.publicar(Publicacion(tema, "", 1, True))


def cliente_mqtt(request: Request) -> ClienteMqtt:
    return request.app.state.mqtt


ClienteMqttDeLaApp = Annotated[ClienteMqtt, Depends(cliente_mqtt)]


async def resumen_periodico(cliente: ClienteMqtt, intervalo_s: float = INTERVALO_RESUMEN_S) -> None:
    """Publica el resumen cada 5 minutos mientras el servidor esté arriba."""
    while True:
        await asyncio.sleep(intervalo_s)
        await run_in_threadpool(cliente.publicar_resumen)


def publicar_una_vez(url: str, publicaciones: Sequence[Publicacion], espera_s: float = 5) -> bool:
    """Publica con una conexión corta, para otro proceso como el comando crear-camara. El client id vacío lo asigna el
    broker, así no saca al servidor. Devuelve False si el broker no respondió o no confirmó algo."""
    partes = urlsplit(url)
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="", clean_session=True, protocol=mqtt.MQTTv311)
    if (credenciales := _usuario_y_clave(partes)) is not None:
        cliente.username_pw_set(*credenciales)
    respuesta: dict[str, bool] = {}
    llego = threading.Event()

    def al_conectar(_cliente, _datos, _banderas, codigo, _propiedades) -> None:
        respuesta["aceptada"] = not codigo.is_failure
        llego.set()

    cliente.on_connect = al_conectar
    try:
        cliente.connect(partes.hostname or "localhost", partes.port or 1883, keepalive=10)
    except OSError:
        return False
    cliente.loop_start()
    try:
        if not llego.wait(espera_s) or not respuesta.get("aceptada"):
            return False
        enviados = [cliente.publish(p.tema, p.carga, qos=p.qos, retain=p.retenido) for p in publicaciones]
        for enviado in enviados:
            enviado.wait_for_publish(timeout=espera_s)
        return all(enviado.is_published() for enviado in enviados)
    except (ValueError, RuntimeError):
        return False
    finally:
        cliente.disconnect()
        cliente.loop_stop()
