"""
Nombre: extraer.py
Descripción: Modo extraer de las cámaras de respaldo (RF-10 · C4, api-dispositivo.md): el servidor pide un cuadro completo a la URL de captura de cada cámara de tipo respaldo activa, recorta la cara más grande como lo haría la cámara y la procesa por el mismo camino de enviarRostro. Una tarea por cámara, en paralelo, que arranca y se detiene con el servidor.
Fecha de creación: 2026-11-18
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.0

Lo que el contrato no dice y se decidió en B2 del Día 4 (servidor/README.md, «Modo extraer»):
- el ritmo es el de la cámara: 1 s desde que termina un cuadro, y 3 s después de permitido, denegado o desconocido;
- solo http y https, sin seguir redirecciones, con 3 s de espera en total y un tope de 2 MB por cuadro;
- si la URL falla, se reintenta con espera de 1, 2, 4, 8 y hasta 10 s, como la cámara con un 5xx. El registro lo
  dice una vez por motivo y otra cuando vuelve a capturar, nunca una línea por segundo.
El cuadro y el recorte solo viven en memoria (RNF-01 · C1).
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

import cv2
import httpx
from fastapi.responses import JSONResponse
from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from accesia import rostros, tiempo
from accesia.config import configuracion
from accesia.db import transaccion
from accesia.mqtt import Pendiente
from accesia.vision import Vision, decodificar_jpeg, recortar_cara_mas_grande

registro = logging.getLogger(__name__)

# api-dispositivo.md, «Modo extraer» y «Qué hace la cámara con la respuesta».
ESPERA_S = 1
ESPERA_TRAS_EVENTO_S = 3
TIEMPO_DE_ESPERA_S = 3
# Como la cámara con un 5xx: 1, 2, 4 y hasta 10 s.
ESPERAS_TRAS_FALLA_S = (1, 2, 4, 8, 10)
# Los 100 KB del contrato son para recortes. Un cuadro completo de un ESP32-CAM en UXGA pesa unos 100 a 250 KB y una
# foto 1080p de un celular, menos de 1 MB; más de 2 MB suele ser un video (MJPEG) o algo que no es una foto.
TOPE_CUADRO_BYTES = 2 * 1024 * 1024
# Cada cuánto el supervisor busca cámaras de respaldo nuevas o reactivadas.
REVISAR_CAMARAS_S = 5
CALIDAD_JPEG = 80  # la del recorte de la cámara (api-dispositivo.md)
FIRMWARE = "modo-extraer"  # va en la línea INFO de cada recorte, como el X-AccesIA-Firmware de una cámara
RESULTADOS_CON_EVENTO = ("permitido", "denegado", "desconocido")

AbrirConexion = Callable[[], contextlib.AbstractContextManager[Connection]]


@dataclass(frozen=True)
class Paso:
    """Lo que pasó en una captura y cuánto esperar antes de la siguiente."""

    sigue: bool
    espera: float = 0
    resultado: str | None = None
    falla: str | None = None


class FallaDeCaptura(Exception):
    """La URL de captura no entregó un JPEG. El motivo va al registro; la imagen, nunca."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


def url_para_el_registro(url: str) -> str:
    """La URL sin usuario, clave ni parámetros: lo demás basta para saber a qué cámara se le pide."""
    partes = urlsplit(url)
    servidor = partes.hostname or ""
    if partes.port is not None:
        servidor += f":{partes.port}"
    return f"{partes.scheme}://{servidor}{partes.path}"


def segundos(valor: float) -> str:
    return f"{valor:g}".replace(".", ",")


def tamano(cantidad: int) -> str:
    megas = 1024 * 1024
    return f"{cantidad // megas} MB" if cantidad >= megas and cantidad % megas == 0 else f"{cantidad} bytes"


def extraer_recorte(datos: bytes, vision: Vision, cara_min_px: int) -> bytes | None:
    """Lo que haría la cámara con el cuadro: la cara más grande, recortada con la fórmula del contrato, en un JPEG
    de calidad 80. None si no hay una cara de al menos CARA_MIN_PX. Todo en memoria."""
    cuadro = decodificar_jpeg(datos)
    if cuadro is None:
        raise FallaDeCaptura("no devolvió un JPEG")
    recorte = recortar_cara_mas_grande(cuadro, vision, cara_min_px)
    if recorte is None:
        return None
    _ok, jpeg = cv2.imencode(".jpg", recorte, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG])
    return jpeg.tobytes()


def url_vigente(conexion: Connection, codigo: str) -> str | None:
    """La URL de captura si la cámara sigue activa y de tipo respaldo; None si se desactivó, se borró o cambió."""
    return conexion.execute(
        text("SELECT url_captura FROM dispositivo WHERE codigo = :codigo AND tipo = 'respaldo' AND activo"),
        {"codigo": codigo},
    ).scalar_one_or_none()


def camaras_de_respaldo(conexion: Connection) -> list[tuple[str, str]]:
    filas = conexion.execute(
        text(
            "SELECT codigo, url_captura FROM dispositivo "
            "WHERE tipo = 'respaldo' AND activo AND url_captura IS NOT NULL ORDER BY codigo"
        )
    )
    return [(fila.codigo, fila.url_captura) for fila in filas]


class ModoExtraer:
    """Pide los cuadros de las cámaras de respaldo. Lee la visión, las alertas y MQTT del estado de la app cuando los
    necesita, porque el arranque y las pruebas los ponen después de crearlo."""

    def __init__(
        self,
        estado,
        *,
        conexiones: AbrirConexion = transaccion,
        transporte: httpx.AsyncBaseTransport | None = None,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        tiempo_de_espera_s: float = TIEMPO_DE_ESPERA_S,
        tope_bytes: int = TOPE_CUADRO_BYTES,
        revisar_cada_s: float = REVISAR_CAMARAS_S,
    ) -> None:
        self._estado = estado
        self._conexiones = conexiones
        self._transporte = transporte
        self._dormir = dormir
        self._tiempo_de_espera_s = tiempo_de_espera_s
        self._tope_bytes = tope_bytes
        self._revisar_cada_s = revisar_cada_s
        self._http: httpx.AsyncClient | None = None
        # Por cámara: cuántas capturas seguidas fallaron y el último motivo que se avisó en el registro.
        self._fallas: dict[str, tuple[int, str]] = {}
        self._base_avisada = False

    # --- Una captura ---

    async def una_captura(self, codigo: str) -> Paso:
        """Revisa la cámara, pide un cuadro, lo recorta y lo procesa. Un error no sale de aquí: vuelve como falla."""
        inicio = time.perf_counter()
        try:
            url = await run_in_threadpool(self._url_vigente, codigo)
            if url is None:
                return Paso(sigue=False)
            datos = await self._pedir(url)
            recorte = await run_in_threadpool(
                extraer_recorte, datos, self._estado.vision, configuracion().cara_min_px
            )
            momento = tiempo.ahora()
            vigente, respuesta, pendiente = await run_in_threadpool(
                self._registrar, codigo, url, recorte, momento, inicio
            )
        except FallaDeCaptura as falla:
            return self._fallo(codigo, f"la URL de captura {falla.motivo}")
        except SQLAlchemyError:
            return self._fallo(codigo, "la base no respondió")
        except Exception as error:  # un error inesperado no tumba el bucle: se avisa con su traza y se reintenta
            return self._fallo(codigo, f"el modo extraer falló ({type(error).__name__})", con_traza=True)
        if not vigente:
            return Paso(sigue=False)
        self._volvio(codigo)
        if pendiente is not None:
            # Como en enviarRostro: después de confirmar la transacción, y el cliente publica solo con conexión.
            await run_in_threadpool(self._estado.mqtt.publicar_recorte, pendiente)
        resultado = respuesta.resultado if respuesta is not None else None
        espera = ESPERA_TRAS_EVENTO_S if resultado in RESULTADOS_CON_EVENTO else ESPERA_S
        return Paso(sigue=True, espera=espera, resultado=resultado)

    def _url_vigente(self, codigo: str) -> str | None:
        with self._conexiones() as conexion:
            return url_vigente(conexion, codigo)

    async def _pedir(self, url: str) -> bytes:
        """GET a la URL de captura, con el tiempo de espera para todo el pedido y sin seguir redirecciones."""
        if urlsplit(url).scheme not in ("http", "https"):
            raise FallaDeCaptura("no es http ni https")
        if self._http is not None:
            return await self._pedir_con(self._http, url)
        async with self._cliente() as cliente:
            return await self._pedir_con(cliente, url)

    async def _pedir_con(self, cliente: httpx.AsyncClient, url: str) -> bytes:
        try:
            async with asyncio.timeout(self._tiempo_de_espera_s):
                async with cliente.stream("GET", url) as respuesta:
                    if 300 <= respuesta.status_code < 400:
                        raise FallaDeCaptura("redirige a otra dirección: pon la URL final")
                    if respuesta.status_code != 200:
                        raise FallaDeCaptura(f"respondió {respuesta.status_code}")
                    tope = f"devolvió más de {tamano(self._tope_bytes)}"
                    largo = respuesta.headers.get("content-length")
                    if largo is not None and largo.isdigit() and int(largo) > self._tope_bytes:
                        raise FallaDeCaptura(tope)
                    datos = bytearray()
                    async for trozo in respuesta.aiter_bytes():
                        datos += trozo
                        if len(datos) > self._tope_bytes:
                            raise FallaDeCaptura(tope)
                    return bytes(datos)
        except (TimeoutError, httpx.TimeoutException):
            raise FallaDeCaptura(f"no respondió en {segundos(self._tiempo_de_espera_s)} s") from None
        except httpx.InvalidURL:
            raise FallaDeCaptura("no es una URL válida") from None
        except httpx.HTTPError:
            raise FallaDeCaptura("no se pudo alcanzar") from None

    def _registrar(
        self, codigo: str, url: str, recorte: bytes | None, momento: datetime, inicio: float
    ) -> tuple[bool, object, Pendiente | None]:
        """En una transacción: la cámara sigue igual, cuenta el contacto y, si hay recorte, lo procesa como un
        enviarRostro. Devuelve si la cámara seguía vigente, la respuesta y lo que hay que publicar después."""
        with self._conexiones() as conexion:
            actual = url_vigente(conexion, codigo)
            if actual is None:
                return False, None, None
            if actual != url:  # cambió la URL mientras se pedía: este cuadro no cuenta, el próximo usa la nueva
                return True, None, None
            conexion.execute(
                text("UPDATE dispositivo SET ultimo_contacto = :momento WHERE codigo = :codigo"),
                {"momento": momento, "codigo": codigo},
            )
            if recorte is None:
                return True, None, None
            camara = rostros.CamaraAutenticada(codigo=codigo, tipo="respaldo", activo=True)
            respuesta, pendiente = rostros.procesar(
                conexion, camara, recorte, self._estado.vision, momento, inicio, FIRMWARE, self._estado.alertas
            )
        if isinstance(respuesta, JSONResponse):  # un recorte que no se pudo leer: no debería pasar con el nuestro
            return True, None, None
        return True, respuesta, pendiente

    def _fallo(self, codigo: str, motivo: str, con_traza: bool = False) -> Paso:
        """Espera cada vez más y lo avisa una vez por motivo, sin una línea por segundo. Se llama dentro del except,
        así que con_traza agrega la del error al aviso."""
        veces, ultimo = self._fallas.get(codigo, (0, ""))
        espera = ESPERAS_TRAS_FALLA_S[min(veces, len(ESPERAS_TRAS_FALLA_S) - 1)]
        if motivo != ultimo:
            registro.warning(
                "Cámara %s: %s. Se reintenta con espera de 1 a 10 s; no se repite este aviso.",
                codigo,
                motivo,
                exc_info=con_traza,
            )
        self._fallas[codigo] = (veces + 1, motivo)
        return Paso(sigue=True, espera=espera, falla=motivo)

    def _volvio(self, codigo: str) -> None:
        if self._fallas.pop(codigo, None) is not None:
            registro.info("Cámara %s: vuelve a capturar.", codigo)

    # --- El bucle de cada cámara y el supervisor ---

    def avisar_inicio(self, codigo: str, url: str) -> None:
        registro.info("Cámara %s: modo extraer, pide %s cada segundo.", codigo, url_para_el_registro(url))

    async def vigilar(self, codigo: str) -> None:
        """Pide cuadros a una cámara hasta que se desactive, se borre o deje de ser de respaldo."""
        while True:
            paso = await self.una_captura(codigo)
            if not paso.sigue:
                self._fallas.pop(codigo, None)
                registro.info(
                    "Cámara %s: deja de pedir cuadros (está desactivada, borrada o no es de respaldo).", codigo
                )
                return
            await self._dormir(paso.espera)

    async def correr(self) -> None:
        """Mientras el servidor esté arriba: cada pocos segundos busca las cámaras de respaldo activas y deja una
        tarea pidiendo cuadros a cada una. Se piden en paralelo, así que una lenta no frena a las demás."""
        tareas: dict[str, asyncio.Task] = {}
        async with self._cliente() as cliente:
            self._http = cliente
            try:
                while True:
                    for codigo, url in await self._camaras():
                        tarea = tareas.get(codigo)
                        if tarea is None or tarea.done():
                            self.avisar_inicio(codigo, url)
                            tareas[codigo] = asyncio.create_task(self.vigilar(codigo), name=f"extraer-{codigo}")
                    await self._dormir(self._revisar_cada_s)
            finally:
                for tarea in tareas.values():
                    tarea.cancel()
                await asyncio.gather(*tareas.values(), return_exceptions=True)
                self._http = None

    async def _camaras(self) -> list[tuple[str, str]]:
        try:
            camaras = await run_in_threadpool(self._leer_camaras)
        except SQLAlchemyError:
            if not self._base_avisada:
                registro.warning("Modo extraer: la base no respondió; se vuelve a intentar cada %s s.",
                                 segundos(self._revisar_cada_s))
                self._base_avisada = True
            return []
        if self._base_avisada:
            registro.info("Modo extraer: la base volvió a responder.")
            self._base_avisada = False
        return camaras

    def _leer_camaras(self) -> list[tuple[str, str]]:
        with self._conexiones() as conexion:
            return camaras_de_respaldo(conexion)

    def _cliente(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self._transporte,
            follow_redirects=False,
            timeout=httpx.Timeout(self._tiempo_de_espera_s),
        )
