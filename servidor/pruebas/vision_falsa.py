"""
Nombre: vision_falsa.py
Descripción: Visión armada para las pruebas de las reglas: caras con puntaje, tamaño, nitidez y huella elegidos, sin fotos. Incluye huellas de prueba con similitudes exactas y una cámara que envía recortes al servidor.
Fecha de creación: 2026-11-12
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.1
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import cv2
import numpy as np
from fastapi.testclient import TestClient
from httpx import Response

from accesia.vision import Cara, Huella

DIMENSION = 128

# Un JPEG gris de 120 × 150 sin cara: la visión armada no mira sus píxeles.
_ok, _jpeg = cv2.imencode(".jpg", np.full((150, 120, 3), 128, dtype=np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 80])
JPEG = _jpeg.tobytes()


def eje(indice: int) -> list[float]:
    """Una huella de norma 1 en un solo eje: dos ejes distintos tienen similitud 0."""
    vector = [0.0] * DIMENSION
    vector[indice] = 1.0
    return vector


def parecida(similitud: float, base: int = 0, libre: int = 1) -> list[float]:
    """Una huella de norma 1 con esa similitud (coseno) respecto de eje(base).

    Dos huellas parecidas a la misma base, con ejes libres distintos, tienen similitud s1 × s2 entre ellas.
    """
    vector = [0.0] * DIMENSION
    vector[base] = similitud
    vector[libre] = math.sqrt(1 - similitud * similitud)
    return vector


@dataclass
class CaraArmada:
    """Una cara como la vería YuNet + SFace, con los valores que la prueba necesita."""

    alto: float = 120
    huella: Sequence[float] = field(default_factory=lambda: eje(0))
    puntaje: float = 0.95
    nitidez: float = 150.0
    ancho: float | None = None  # por defecto, 0,8 × alto
    x: float = 10.0
    y: float = 10.0

    def cara(self) -> Cara:
        return Cara(x=self.x, y=self.y, ancho=self.ancho or self.alto * 0.8, alto=self.alto, puntaje=self.puntaje)


class VisionFalsa:
    """Cumple la interfaz Vision devolviendo las caras armadas para el próximo recorte."""

    def __init__(self) -> None:
        self._armadas: list[CaraArmada] = []
        self._entregadas: list[tuple[Cara, CaraArmada]] = []
        self.imagenes = 0
        self.formas: list[tuple[int, int]] = []  # (alto, ancho) de cada imagen que vio, en orden

    def preparar(self, caras: Sequence[CaraArmada]) -> None:
        self._armadas = list(caras)

    def detectar(self, imagen: np.ndarray) -> list[Cara]:
        self.imagenes += 1
        self.formas.append(tuple(imagen.shape[:2]))
        self._entregadas = [(armada.cara(), armada) for armada in self._armadas]
        return [cara for cara, _ in self._entregadas]

    def huella(self, imagen: np.ndarray, cara: Cara) -> Huella:
        for entregada, armada in self._entregadas:
            if entregada is cara:
                vector = np.asarray(armada.huella, dtype=np.float32)
                return Huella(vector=vector / np.linalg.norm(vector), nitidez=armada.nitidez)
        raise AssertionError("Se pidió la huella de una cara que la visión no entregó.")


@dataclass
class CamaraDePrueba:
    """Una cámara registrada en la base con su token, que envía recortes como dice api-dispositivo.md."""

    cliente: TestClient
    codigo: str
    token: str
    vision: VisionFalsa

    @property
    def ruta(self) -> str:
        return f"/api/v1/dispositivos/{self.codigo}/rostros"

    def enviar(
        self,
        *caras: CaraArmada,
        datos: bytes = JPEG,
        token: str | None = None,
        tipo: str = "image/jpeg",
        cabeceras: dict[str, str] | None = None,
    ) -> Response:
        """Envía un recorte. La visión armada ve esas caras (ninguna, si no se pasa ninguna)."""
        self.vision.preparar(caras)
        encabezado = {"Authorization": f"Bearer {token or self.token}", "Content-Type": tipo}
        encabezado.update(cabeceras or {})
        return self.cliente.post(self.ruta, content=datos, headers=encabezado)
