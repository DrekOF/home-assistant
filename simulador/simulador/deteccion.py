"""
Nombre: deteccion.py
Descripción: Detección de caras con YuNet (cv2.FaceDetectorYN) y la interfaz Detector que las pruebas reemplazan por un doble.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from simulador.recorte import Cara

# Puntaje mínimo de YuNet, el del paso 1 de R7 (specs/reglas.md).
PUNTAJE_MIN = 0.9
# Valores habituales de YuNet en opencv_zoo para descartar cajas repetidas.
UMBRAL_NMS = 0.3
MAX_CARAS = 5000


class Detector(Protocol):
    def detectar(self, imagen: np.ndarray) -> list[Cara]:
        """Las caras del cuadro, en píxeles de esa misma imagen."""
        ...


class DetectorYuNet:
    def __init__(self, modelo: Path, puntaje_min: float = PUNTAJE_MIN) -> None:
        self._detector = cv2.FaceDetectorYN.create(str(modelo), "", (320, 240), puntaje_min, UMBRAL_NMS, MAX_CARAS)

    def detectar(self, imagen: np.ndarray) -> list[Cara]:
        alto, ancho = imagen.shape[:2]
        self._detector.setInputSize((ancho, alto))
        _, caras = self._detector.detect(imagen)
        if caras is None:
            return []
        # Cada fila: x, y, w, h, cinco puntos de referencia (10 números) y el puntaje al final.
        return [Cara(float(f[0]), float(f[1]), float(f[2]), float(f[3]), float(f[14])) for f in caras]
