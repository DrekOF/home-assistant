"""
Nombre: dobles.py
Descripción: Dobles de prueba del simulador: detector, reloj, servidor (httpx.MockTransport), webcam, ventana y cliente MQTT falsos, y fotos sintéticas sin caras.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
import paho.mqtt.client as paho
import pytest
from paho.mqtt.client import ConnectFlags, DisconnectFlags, MQTTMessage
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

import simulador.comandos as comandos
from simulador.envio import ClienteCamara
from simulador.recorte import Cara

# Si este texto aparece en la salida, el simulador mostró el token.
TOKEN = "token-de-prueba-que-nunca-se-muestra"
SERVIDOR = "http://servidor.prueba"


class DetectorFalso:
    """Devuelve las caras que se le dan. Con `por_llamada`, una lista por llamada (una por foto o por cuadro)."""

    def __init__(self, caras: Sequence[Cara] = (), *, por_llamada: Sequence[Sequence[Cara]] | None = None) -> None:
        self._caras = list(caras)
        self._por_llamada = [list(lista) for lista in por_llamada] if por_llamada is not None else None
        self.formas: list[tuple[int, ...]] = []

    def detectar(self, imagen: np.ndarray) -> list[Cara]:
        self.formas.append(imagen.shape)
        if self._por_llamada is None:
            return list(self._caras)
        indice = len(self.formas) - 1
        return list(self._por_llamada[indice]) if indice < len(self._por_llamada) else []


class RelojFalso:
    """Reloj que solo avanza cuando se le pide: sirve de reloj del Ritmo y de `dormir`."""

    def __init__(self, inicio: float = 1000.0) -> None:
        self.ahora = inicio
        self.dormidas: list[float] = []

    def __call__(self) -> float:
        return self.ahora

    def dormir(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.ahora += segundos


def cuerpo_200(
    resultado: str,
    *,
    modo: str = "reconocer",
    motivo: str | None = None,
    persona: str | None = None,
    similitud: float | None = None,
    repetido: bool = False,
    inscripcion: dict[str, Any] | None = None,
    mensaje: str = "",
) -> dict[str, Any]:
    """Una respuesta 200 con todos los campos del contrato (api-dispositivo.md · Respuesta 200)."""
    return {
        "modo": modo,
        "resultado": resultado,
        "motivo": motivo,
        "persona": None if persona is None else {"id": "01a1e5c2-7f3a-7b2c-9d4e-5f6a7b8c9d0e", "nombre": persona},
        "similitud": similitud,
        "repetido": repetido,
        "evento_id": None,
        "inscripcion": inscripcion,
        "mensaje": mensaje,
        "hora": "2026-11-20T07:58:12-05:00",
    }


def respuesta_200(resultado: str, **campos: Any) -> httpx.Response:
    return httpx.Response(200, json=cuerpo_200(resultado, **campos))


def respuesta_error(estado: int, codigo: str, cabeceras: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(estado, json={"detalle": f"error {codigo}", "codigo": codigo}, headers=cabeceras)


Siguiente = httpx.Response | Exception | Callable[[httpx.Request], httpx.Response]


class ServidorFalso:
    """Servidor con httpx.MockTransport: guarda cada petición y responde, en orden, lo que se le dio.

    Cuando se acaban las respuestas, contesta `descartado`. `al_recibir` corre con cada petición (por ejemplo,
    para que el reloj falso avance lo que tarda el servidor).
    """

    def __init__(self, *respuestas: Siguiente, al_recibir: Callable[[httpx.Request], None] | None = None) -> None:
        self.respuestas: list[Siguiente] = list(respuestas)
        self.peticiones: list[httpx.Request] = []
        self.al_recibir = al_recibir

    def _manejar(self, peticion: httpx.Request) -> httpx.Response:
        peticion.read()
        self.peticiones.append(peticion)
        if self.al_recibir is not None:
            self.al_recibir(peticion)
        siguiente = self.respuestas.pop(0) if self.respuestas else respuesta_200("descartado", motivo="sin_cara")
        if isinstance(siguiente, Exception):
            raise siguiente
        if callable(siguiente):
            return siguiente(peticion)
        return siguiente

    def cliente(self, codigo: str = "entrada") -> ClienteCamara:
        return ClienteCamara(SERVIDOR, codigo, TOKEN, transporte=httpx.MockTransport(self._manejar))


class CapturaFalsa:
    """Webcam falsa: entrega los cuadros que se le dan y después falla, como una cámara desconectada."""

    def __init__(self, cuadros: Sequence[np.ndarray], abierta: bool = True) -> None:
        self._cuadros = list(cuadros)
        self._abierta = abierta
        self.liberada = False

    def isOpened(self) -> bool:  # noqa: N802 (nombre de OpenCV)
        return self._abierta

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._cuadros:
            return False, None
        return True, self._cuadros.pop(0)

    def release(self) -> None:
        self.liberada = True


class VentanaFalsa:
    """Ventana falsa: muestra `cuadros` imágenes y después responde como si la persona pulsara q.

    Guarda en memoria la última imagen que mostró, para mirar lo que dibujó el simulador.
    """

    def __init__(self, cuadros: int) -> None:
        self._faltan = cuadros
        self.formas: list[tuple[int, ...]] = []
        self.ultima: np.ndarray | None = None
        self.cerrada = False

    def mostrar(self, imagen: np.ndarray) -> bool:
        self.formas.append(imagen.shape)
        self.ultima = imagen
        self._faltan -= 1
        return self._faltan > 0

    def cerrar(self) -> None:
        self.cerrada = True


def imagen_sintetica(ancho: int, alto: int, semilla: int = 0) -> np.ndarray:
    """Degradado con unas figuras: no es una cara, pero tampoco es plana (el JPEG tiene algo que comprimir)."""
    generador = np.random.default_rng(semilla)
    columnas = np.linspace(0, 255, ancho, dtype=np.float32)
    filas = np.linspace(0, 255, alto, dtype=np.float32)[:, None]
    imagen = np.stack([columnas + 0 * filas, filas + 0 * columnas, (columnas + filas) / 2], axis=2).astype(np.uint8)
    for _ in range(6):
        centro = (int(generador.integers(0, ancho)), int(generador.integers(0, alto)))
        color = tuple(int(c) for c in generador.integers(0, 256, 3))
        cv2.circle(imagen, centro, int(generador.integers(5, max(6, min(ancho, alto) // 6))), color, -1)
    return imagen


def ruido(ancho: int, alto: int, semilla: int = 0) -> np.ndarray:
    """Ruido puro: su JPEG pesa mucho, sirve para pasar de 100 000 bytes."""
    return np.random.default_rng(semilla).integers(0, 256, (alto, ancho, 3), dtype=np.uint8)


def escribir_foto(ruta: Path, imagen: np.ndarray) -> Path:
    """Escribe una foto sintética de entrada para el modo carpeta (la prueba la crea; el simulador solo la lee)."""
    ok, datos = cv2.imencode(ruta.suffix, imagen)
    assert ok
    ruta.write_bytes(datos.tobytes())
    return ruta


# --- MQTT ---

# Clave de prueba del usuario camara: si aparece en la salida, el simulador mostró la clave.
CLAVE_MQTT = "clave-mqtt-de-prueba-que-nunca-se-muestra"


@dataclass(frozen=True)
class Publicado:
    tema: str
    carga: str
    qos: int
    retenido: bool


class InfoFalsa:
    """Como MQTTMessageInfo: el broker falso confirma en el acto."""

    def wait_for_publish(self, timeout: float | None = None) -> None:
        return None


class SocketFalso:
    def __init__(self, ip: str) -> None:
        self._ip = ip

    def getsockname(self) -> tuple[str, int]:
        return (self._ip, 50123)


class ClienteMqttFalso:
    """paho falso: guarda lo que el simulador configura y publica.

    La prueba hace de broker con `conectar`, `fallar_conexion`, `cortar` y `recibir`, que llaman a los callbacks
    del simulador como lo haría paho desde su hilo.
    """

    def __init__(self, client_id: str, *, ip: str = "192.168.137.50", conectar_al_arrancar: bool = False) -> None:
        self.client_id = client_id
        self.ip = ip
        self.conectar_al_arrancar = conectar_al_arrancar
        self.usuario: str | None = None
        self.clave: str | None = None
        self.ultimo_deseo: Publicado | None = None
        self.esperas: tuple[int, int] | None = None
        self.conexion: tuple[str, int, int] | None = None
        self.bucle = False
        self.desconexiones = 0
        self.publicados: list[Publicado] = []
        self.suscripciones: list[tuple[str, int]] = []
        self.on_connect: Any = None
        self.on_connect_fail: Any = None
        self.on_disconnect: Any = None
        self.on_message: Any = None

    # --- Lo que llama el simulador ---

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        self.usuario, self.clave = username, password

    def will_set(self, topic: str, payload: str | None = None, qos: int = 0, retain: bool = False,
                 properties: Any = None) -> None:
        self.ultimo_deseo = Publicado(topic, payload or "", qos, retain)

    def reconnect_delay_set(self, min_delay: int = 1, max_delay: int = 120) -> None:
        self.esperas = (min_delay, max_delay)

    def connect_async(self, host: str, port: int = 1883, keepalive: int = 60, **_: Any) -> None:
        self.conexion = (host, port, keepalive)

    def loop_start(self) -> None:
        self.bucle = True
        if self.conectar_al_arrancar:
            self.conectar()

    def loop_stop(self) -> None:
        self.bucle = False

    def subscribe(self, topic: str, qos: int = 0, **_: Any) -> None:
        self.suscripciones.append((topic, qos))

    def publish(self, topic: str, payload: str | None = None, qos: int = 0, retain: bool = False,
                properties: Any = None) -> InfoFalsa:
        self.publicados.append(Publicado(topic, payload or "", qos, retain))
        return InfoFalsa()

    def disconnect(self, reasoncode: Any = None, properties: Any = None) -> None:
        self.desconexiones += 1

    def socket(self) -> SocketFalso:
        return SocketFalso(self.ip)

    # --- Lo que haría el broker ---

    def conectar(self, codigo: int = 0) -> None:
        """CONNACK: 0 acepta; 0x86 (134) es «usuario o clave incorrectos»."""
        self.on_connect(self, None, ConnectFlags(session_present=False),
                        ReasonCode(PacketTypes.CONNACK, identifier=codigo), Properties(PacketTypes.CONNACK))

    def fallar_conexion(self) -> None:
        """No se pudo abrir la conexión: el broker no está."""
        self.on_connect_fail(self, None)

    def cortar(self, codigo: int = 0x80, *, desde_broker: bool = False) -> None:
        """Se cayó la conexión (0x80, como paho cuando se pierde) o el broker la cerró (0x8E: sesión tomada)."""
        self.on_disconnect(self, None, DisconnectFlags(is_disconnect_packet_from_server=desde_broker),
                           ReasonCode(PacketTypes.DISCONNECT, identifier=codigo), Properties(PacketTypes.DISCONNECT))

    def recibir(self, tema: str, carga: bytes) -> None:
        mensaje = MQTTMessage(topic=tema.encode())
        mensaje.payload = carga
        self.on_message(self, None, mensaje)

    def en(self, tema: str) -> list[Publicado]:
        return [publicado for publicado in self.publicados if publicado.tema == tema]


class FabricaMqtt:
    """El `crear_cliente` de PuertaMqtt para las pruebas: crea clientes falsos y los guarda en `clientes`."""

    def __init__(self, **opciones: Any) -> None:
        self._opciones = opciones
        self.clientes: list[ClienteMqttFalso] = []

    def __call__(self, codigo: str) -> ClienteMqttFalso:
        cliente = ClienteMqttFalso(codigo, **self._opciones)
        self.clientes.append(cliente)
        return cliente


def preparar_principal(
    monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, caras: Sequence[Cara] = ()
) -> list[ClienteMqttFalso]:
    """Deja correr principal() sin modelo, sin servidor y sin broker: detector, servidor y paho falsos.

    Devuelve la lista de los clientes MQTT que cree el simulador; cada uno se conecta al arrancar.
    """
    monkeypatch.setattr(comandos, "asegurar_modelo", lambda: Path("modelo-falso.onnx"))
    monkeypatch.setattr(comandos, "DetectorYuNet", lambda modelo, puntaje: DetectorFalso(caras))
    monkeypatch.setattr(comandos, "ClienteCamara", lambda url, codigo, token: servidor.cliente(codigo))
    creados: list[ClienteMqttFalso] = []

    def crear(*_args: Any, client_id: str, **_kwargs: Any) -> ClienteMqttFalso:
        cliente = ClienteMqttFalso(client_id, conectar_al_arrancar=True)
        creados.append(cliente)
        return cliente

    monkeypatch.setattr(paho, "Client", crear)
    monkeypatch.setenv("TOKEN_CAMARA", TOKEN)
    monkeypatch.setenv("MQTT_CAMARA_CLAVE", CLAVE_MQTT)
    return creados
