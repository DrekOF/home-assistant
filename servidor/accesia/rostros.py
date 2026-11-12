"""
Nombre: rostros.py
Descripción: Recortes que envía la cámara (enviarRostro, api-dispositivo.md): token, tipo, tamaño, ritmo (429) e imagen, en ese orden; y el modo de la cámara: inscribir si tiene una inscripción activa (R7 y R9), reconocer si no (R1 a R4).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import hashlib
import hmac
import logging
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import Connection, text

from accesia.errores import CodigoError, ErrorAccesIA, respuesta_error
from accesia.esquemas import RespuestaRostro
from accesia.inscripciones import activa_de, procesar_muestra, vencer_inscripciones
from accesia.reconocimiento import reconocer
from accesia.seguridad import hash_de_token
from accesia.vision import Vision, decodificar_jpeg

registro = logging.getLogger(__name__)

# 100 KB del contrato = 102 400 bytes (api-dispositivo.md 1.2).
LIMITE_BYTES = 100 * 1024
# Dos recortes de la misma cámara con menos de esto entre sí: 429 con Retry-After: 1 (api-dispositivo.md).
ESPACIO_MINIMO_S = 0.8
REINTENTAR_EN_S = "1"

# Se compara contra esto cuando la cámara no existe, para que el 401 tarde lo mismo en los tres casos.
_HASH_DE_RELLENO = hashlib.sha256(b"camara-que-no-existe").hexdigest()
_CODIGO_VALIDO = re.compile(r"^[a-z0-9-]{3,32}$")


class ControlDeRitmo:
    """El 429 en memoria, por cámara: el servidor corre con un solo proceso (arquitectura.md).

    Cuenta desde el último recorte aceptado; un recorte rechazado con 429 no mueve el reloj.
    """

    def __init__(self, espacio_s: float = ESPACIO_MINIMO_S, reloj: Callable[[], float] = time.monotonic) -> None:
        self._espacio_s = espacio_s
        self._reloj = reloj
        self._ultimo: dict[str, float] = {}
        self._candado = threading.Lock()

    def permitir(self, codigo: str) -> bool:
        with self._candado:
            ahora = self._reloj()
            ultimo = self._ultimo.get(codigo)
            if ultimo is not None and ahora - ultimo < self._espacio_s:
                return False
            self._ultimo[codigo] = ahora
            return True


@dataclass(frozen=True)
class CamaraAutenticada:
    codigo: str
    tipo: str
    activo: bool


def para_el_registro(texto: str | None, largo: int = 60) -> str:
    """Un valor que manda el cliente, recortado y sin caracteres raros, para escribirlo en el registro sin riesgo."""
    return re.sub(r"[^\w.+-]", "?", (texto or "")[:largo])


def _token_de(autorizacion: str | None) -> str | None:
    if not autorizacion:
        return None
    esquema, _, token = autorizacion.partition(" ")
    token = token.strip()
    return token if esquema.lower() == "bearer" and token else None


def autenticar(conexion: Connection, codigo: str, autorizacion: str | None, momento: datetime) -> CamaraAutenticada:
    """Token Bearer comparado por su SHA-256 (RNF-02 · C1). Con token válido actualiza el último contacto.

    Si falta el token, no corresponde o la cámara no existe, responde lo mismo: 401 token_invalido.
    """
    token = _token_de(autorizacion)
    fila = conexion.execute(
        text("SELECT codigo, tipo, activo, token_hash FROM dispositivo WHERE codigo = :codigo"), {"codigo": codigo}
    ).one_or_none()
    esperado = fila.token_hash if fila is not None else _HASH_DE_RELLENO
    correcto = hmac.compare_digest(hash_de_token(token or ""), esperado)
    if token is None or fila is None or not correcto:
        nombre = codigo if _CODIGO_VALIDO.match(codigo) else "(código no válido)"
        registro.info("Cámara %s: 401 token_invalido.", nombre)
        raise ErrorAccesIA(401, "token_invalido", "El token de la cámara no es válido.")
    conexion.execute(
        text("UPDATE dispositivo SET ultimo_contacto = :momento WHERE codigo = :codigo"),
        {"momento": momento, "codigo": fila.codigo},
    )
    return CamaraAutenticada(codigo=fila.codigo, tipo=fila.tipo, activo=fila.activo)


def rechazo(
    camara: CamaraAutenticada, estado: int, codigo: CodigoError, detalle: str, cabeceras: dict[str, str] | None = None
) -> JSONResponse:
    """Un error después del token. Se responde sin lanzar la excepción para no deshacer el último contacto."""
    registro.info("Cámara %s: %d %s.", camara.codigo, estado, codigo)
    return respuesta_error(estado, codigo, detalle, cabeceras)


def es_jpeg(tipo: str | None) -> bool:
    """Content-Type image/jpeg, con o sin parámetros y sin importar mayúsculas."""
    return (tipo or "").split(";", 1)[0].strip().lower() == "image/jpeg"


async def leer_cuerpo(request: Request, tope: int = LIMITE_BYTES) -> bytes | None:
    """El cuerpo completo en memoria, o None si pasa del tope. No lo lee entero si ya se sabe que es más grande."""
    largo = request.headers.get("content-length", "")
    if largo.isdigit() and int(largo) > tope:
        return None
    partes = bytearray()
    async for parte in request.stream():
        partes.extend(parte)
        if len(partes) > tope:
            return None
    return bytes(partes)


def procesar(
    conexion: Connection,
    camara: CamaraAutenticada,
    datos: bytes,
    vision: Vision,
    momento: datetime,
    inicio: float,
    firmware: str | None = None,
) -> RespuestaRostro | JSONResponse:
    """Decodifica el recorte, decide el modo y aplica las reglas. La imagen solo vive en memoria (RF-04 · C4)."""
    imagen = decodificar_jpeg(datos)
    if imagen is None:
        return rechazo(camara, 422, "imagen_invalida", "El cuerpo no es un JPEG que se pueda leer.")
    caras = vision.detectar(imagen)

    def huella_de(cara):
        return vision.huella(imagen, cara)

    # Antes de decidir el modo, vence la inscripción de la cámara si ya pasó su hora (R9).
    vencer_inscripciones(conexion, momento, camara.codigo)
    inscripcion = activa_de(conexion, camara.codigo)
    if inscripcion is None:
        respuesta, calidad = reconocer(conexion, camara.codigo, caras, huella_de, momento)
    else:
        respuesta, calidad = procesar_muestra(conexion, inscripcion, camara.tipo, caras, huella_de, momento)
    _registrar(camara.codigo, respuesta, calidad, (time.perf_counter() - inicio) * 1000, firmware)
    return respuesta


def _registrar(
    codigo: str, respuesta: RespuestaRostro, calidad: float | None, milisegundos: float, firmware: str | None
) -> None:
    """Una línea INFO por recorte, para depurar y medir. Sin imagen y sin decir a quién se parece un desconocido."""
    partes = [f"Cámara {codigo}", respuesta.modo, respuesta.resultado + (f" ({respuesta.motivo})" if respuesta.motivo else "")]
    if respuesta.repetido:
        partes.append("repetido")
    if respuesta.similitud is not None:
        partes.append(f"similitud {respuesta.similitud:.3f}")
    if calidad is not None:
        partes.append(f"calidad {calidad:.1f}")
    if respuesta.persona is not None:
        partes.append(f"persona {respuesta.persona.id}")
    if respuesta.inscripcion is not None:
        avance = respuesta.inscripcion
        partes.append(f"inscripción {avance.id} {avance.muestras}/{avance.requeridas} {avance.estado}")
    if firmware:
        partes.append(f"firmware {para_el_registro(firmware)}")
    partes.append(f"{milisegundos:.0f} ms")
    registro.info(" · ".join(partes))
