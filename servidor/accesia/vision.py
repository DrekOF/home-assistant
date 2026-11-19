"""
Nombre: vision.py
Descripción: Visión del servidor con la imagen solo en memoria (RF-04 · C1 y C4): decodificar el JPEG, detectar caras con YuNet, recortar con la fórmula del contrato, y sacar la huella con SFace y la nitidez de R7.
Fecha de creación: 2026-11-12
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.1
"""

import logging
import math
import os
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Tope de píxeles al decodificar, antes de importar OpenCV: un JPEG de 100 KB puede declarar un tamaño enorme y
# llenar la memoria de la Raspberry. 4096 × 4096 sobra para un recorte y para un cuadro completo de una cámara.
os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(4096 * 4096))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from accesia.modelos import MODELOS, SFACE, YUNET, carpeta_modelos, problema_de  # noqa: E402

registro = logging.getLogger(__name__)

# R7, paso 1: cuenta como cara la que YuNet detecta con puntaje de 0,9 o más.
UMBRAL_PUNTAJE = 0.9
# R7, paso 3, y contrato de la cámara: el servidor descarta una cara que mide menos de 0,8 × CARA_MIN_PX de alto.
FACTOR_TAMANO = 0.8
# Margen del recorte del contrato (api-dispositivo.md, Fórmula del recorte).
MARGEN = 0.25

_INICIO_JPEG = b"\xff\xd8\xff"


@dataclass(frozen=True)
class Cara:
    """Una cara detectada: caja (x, y, ancho, alto) en píxeles, puntaje de YuNet y sus 5 puntos (10 números)."""

    x: float
    y: float
    ancho: float
    alto: float
    puntaje: float
    puntos: tuple[float, ...] = (0.0,) * 10

    @property
    def area(self) -> float:
        return self.ancho * self.alto

    def fila(self) -> np.ndarray:
        """La fila de 15 números de YuNet, que es lo que espera SFace para alinear."""
        return np.array([self.x, self.y, self.ancho, self.alto, *self.puntos, self.puntaje], dtype=np.float32)


@dataclass(frozen=True)
class Huella:
    """Los 128 números de SFace, normalizados (norma 1), y la nitidez de la cara alineada (R7, paso 4)."""

    vector: np.ndarray
    nitidez: float


class Vision(Protocol):
    """Lo que el servidor necesita de la visión. Las pruebas la reemplazan por caras y huellas armadas."""

    def detectar(self, imagen: np.ndarray) -> list[Cara]: ...

    def huella(self, imagen: np.ndarray, cara: Cara) -> Huella: ...


# --- Imagen y recorte (sin modelos) ---


def decodificar_jpeg(datos: bytes) -> np.ndarray | None:
    """El JPEG en memoria como imagen BGR, o None si no es un JPEG que se pueda leer. Nunca toca el disco."""
    if not datos.startswith(_INICIO_JPEG):
        return None
    try:
        imagen = cv2.imdecode(np.frombuffer(datos, dtype=np.uint8), cv2.IMREAD_COLOR)
    except cv2.error:
        return None
    if imagen is None or imagen.size == 0:
        return None
    return imagen


def caras_validas(caras: Sequence[Cara]) -> list[Cara]:
    """Las caras con puntaje de YuNet de 0,9 o más (R7, paso 1)."""
    return [cara for cara in caras if cara.puntaje >= UMBRAL_PUNTAJE]


def cara_mas_grande(caras: Sequence[Cara]) -> Cara | None:
    """La de mayor área (contrato de la cámara y R7 al reconocer). Si empatan, la primera."""
    mayor = None
    for cara in caras:
        if mayor is None or cara.area > mayor.area:
            mayor = cara
    return mayor


def es_pequena(cara: Cara, cara_min_px: int) -> bool:
    """R7, paso 3: mide menos de 0,8 × CARA_MIN_PX de alto."""
    return cara.alto < FACTOR_TAMANO * cara_min_px


def caja_del_recorte(cara: Cara, ancho: int, alto: int) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) del recorte con 25 % de margen, cortado en el borde del cuadro (api-dispositivo.md).

    x1 e y1 no se incluyen. Es la misma fórmula del firmware y del simulador (casos-recorte.json).
    """
    x0 = max(0, math.floor(cara.x - cara.ancho * MARGEN))
    y0 = max(0, math.floor(cara.y - cara.alto * MARGEN))
    x1 = min(ancho, math.ceil(cara.x + cara.ancho + cara.ancho * MARGEN))
    y1 = min(alto, math.ceil(cara.y + cara.alto + cara.alto * MARGEN))
    return x0, y0, x1, y1


def recortar(imagen: np.ndarray, cara: Cara) -> np.ndarray:
    """El recorte de la cara con la fórmula del contrato, en memoria."""
    alto, ancho = imagen.shape[:2]
    x0, y0, x1, y1 = caja_del_recorte(cara, ancho, alto)
    return imagen[y0:y1, x0:x1]


def recortar_cara_mas_grande(cuadro: np.ndarray, vision: Vision, cara_min_px: int | None = None) -> np.ndarray | None:
    """Lo que hace la cámara antes de enviar: detecta con YuNet en el cuadro completo, elige la cara más grande y la
    recorta con la fórmula del contrato. None si no hay cara.

    Con cara_min_px, tampoco la recorta si mide menos de eso de alto: la cámara no envía caras más pequeñas que
    CARA_MIN_PX (api-dispositivo.md). La usa el modo extraer de la cámara de respaldo (RF-10 · C4), y el recorte
    sigue después el camino de siempre.
    """
    cara = cara_mas_grande(caras_validas(vision.detectar(cuadro)))
    if cara is None or (cara_min_px is not None and cara.alto < cara_min_px):
        return None
    return recortar(cuadro, cara)


def nitidez(alineada: np.ndarray) -> float:
    """R7, paso 4: varianza del laplaciano de la cara alineada de 112 × 112, en gris."""
    gris = cv2.cvtColor(alineada, cv2.COLOR_BGR2GRAY) if alineada.ndim == 3 else alineada
    return float(cv2.Laplacian(gris, cv2.CV_64F).var())


# --- YuNet + SFace ---


class VisionOpenCV:
    """YuNet (detección) y SFace (huella) de opencv_zoo, cargados una sola vez.

    Los objetos de OpenCV no se deben usar desde dos hilos a la vez y FastAPI atiende en varios, así que cada uso
    pasa por un candado.
    """

    def __init__(self, carpeta: Path | None = None) -> None:
        carpeta = carpeta or carpeta_modelos()
        problemas = [problema for modelo in MODELOS if (problema := problema_de(carpeta / modelo.archivo, modelo))]
        if problemas:
            raise RuntimeError(
                "Los modelos de cara no están listos (" + "; ".join(problemas) + "). "
                "Descárgalos con: uv run accesia descargar-modelos (desde servidor/)."
            )
        self._detector = cv2.FaceDetectorYN.create(
            str(carpeta / YUNET.archivo), "", (320, 320), score_threshold=UMBRAL_PUNTAJE
        )
        self._reconocedor = cv2.FaceRecognizerSF.create(str(carpeta / SFACE.archivo), "")
        self._candado = threading.Lock()

    def detectar(self, imagen: np.ndarray) -> list[Cara]:
        alto, ancho = imagen.shape[:2]
        with self._candado:
            self._detector.setInputSize((ancho, alto))
            _, filas = self._detector.detect(imagen)
        if filas is None:
            return []
        return [
            Cara(
                x=float(fila[0]),
                y=float(fila[1]),
                ancho=float(fila[2]),
                alto=float(fila[3]),
                puntaje=float(fila[14]),
                puntos=tuple(float(valor) for valor in fila[4:14]),
            )
            for fila in filas
        ]

    def alinear(self, imagen: np.ndarray, cara: Cara) -> np.ndarray:
        """La cara alineada y recortada a 112 × 112, como la espera SFace."""
        with self._candado:
            return self._reconocedor.alignCrop(imagen, cara.fila())

    def huella_de_alineada(self, alineada: np.ndarray) -> np.ndarray:
        """Los 128 números de SFace para una cara ya alineada de 112 × 112, normalizados (norma 1)."""
        with self._candado:
            vector = self._reconocedor.feature(alineada)
        vector = np.asarray(vector, dtype=np.float32).reshape(-1)
        norma = float(np.linalg.norm(vector))
        if norma == 0.0:
            raise ValueError("SFace devolvió una huella vacía.")
        return vector / norma

    def huella(self, imagen: np.ndarray, cara: Cara) -> Huella:
        alineada = self.alinear(imagen, cara)
        return Huella(vector=self.huella_de_alineada(alineada), nitidez=nitidez(alineada))


def cargar_vision(carpeta: Path | None = None) -> VisionOpenCV:
    """Carga YuNet y SFace una sola vez, al arrancar. Sin los modelos, el servidor no arranca."""
    inicio = time.perf_counter()
    vision = VisionOpenCV(carpeta)
    milisegundos = (time.perf_counter() - inicio) * 1000
    registro.info(
        "Modelos de cara cargados: YuNet 2023mar y SFace 2021dec, OpenCV %s (%.0f ms).", cv2.__version__, milisegundos
    )
    return vision
