"""
Nombre: recortador.py
Descripción: El paso de detectar y recortar, separado del envío y de las esperas: de un cuadro sale el JPEG que se envía o el motivo para no enviar nada.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Es la única pieza que cambia si algún día el simulador tiene que imitar a una cámara que envía el cuadro
completo: otra clase con el mismo método `procesar`, sin tocar el envío ni las esperas. Hoy el contrato
(api-dispositivo.md 1.1) pide el recorte, y es lo único que hay.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from simulador.deteccion import Detector
from simulador.imagen import CALIDAD_JPEG, codificar_jpeg
from simulador.recorte import Cara, Recorte, calcular_recorte, elegir_cara

# Igual que CARA_MIN_PX de infra/.env.example y que el comando cara_min de la cámara.
CARA_MIN = 80
# «Máximo 100 KB» (api-dispositivo.md): se toma la lectura más estricta, 100 000 bytes, para no recibir nunca un 413.
LIMITE_BYTES = 100_000


@dataclass(frozen=True)
class Envio:
    """Lo que se envía: el JPEG, el puntaje para X-AccesIA-Puntaje y, para dibujar, la caja y el recorte."""

    jpeg: bytes
    puntaje: float | None
    caja: Cara | None = None
    recorte: Recorte | None = None


@dataclass(frozen=True)
class SinEnvio:
    """No se envía nada. `motivo` es un código del simulador (no del contrato) y `detalle`, el texto para personas."""

    motivo: str
    detalle: str
    caja: Cara | None = None


class Recortador(Protocol):
    def procesar(self, imagen: np.ndarray) -> Envio | SinEnvio: ...


class RecortadorYuNet:
    """Detecta, descarta las caras de menos de `cara_min` de alto, elige la de mayor área, recorta y comprime."""

    def __init__(
        self,
        detector: Detector,
        cara_min: float = CARA_MIN,
        calidad: int = CALIDAD_JPEG,
        limite_bytes: int = LIMITE_BYTES,
    ) -> None:
        self.detector = detector
        self.cara_min = cara_min
        self.calidad = calidad
        self.limite_bytes = limite_bytes

    def procesar(self, imagen: np.ndarray) -> Envio | SinEnvio:
        caras = self.detector.detectar(imagen)
        if not caras:
            return SinEnvio("sin_cara", "sin cara")

        indice = elegir_cara(caras, self.cara_min)
        if indice is None:
            mayor = max(caras, key=lambda cara: cara.area)
            return SinEnvio(
                "cara_pequena", f"cara pequeña: {mayor.h:.0f} px de alto, el mínimo es {self.cara_min:g}", mayor
            )

        cara = caras[indice]
        alto, ancho = imagen.shape[:2]
        recorte = calcular_recorte(cara, ancho, alto)
        if recorte.vacio:
            return SinEnvio("fuera_del_cuadro", "la cara queda fuera del cuadro", cara)

        jpeg = codificar_jpeg(imagen[recorte.y0 : recorte.y1, recorte.x0 : recorte.x1], self.calidad)
        if len(jpeg) > self.limite_bytes:
            return SinEnvio(
                "recorte_grande",
                f"el recorte pesa {len(jpeg)} bytes y el contrato permite hasta {self.limite_bytes}: no se envía",
                cara,
            )
        return Envio(jpeg, cara.puntaje, cara, recorte)
