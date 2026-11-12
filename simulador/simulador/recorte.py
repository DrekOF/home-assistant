"""
Nombre: recorte.py
Descripción: Elección de la cara y fórmula del recorte de specs/contratos/api-dispositivo.md, sin cámara ni servidor (la misma lógica que accesia_recorte del firmware).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Cara:
    """Caja de una cara: esquina superior izquierda, ancho y alto en píxeles del cuadro, y el puntaje del detector."""

    x: float
    y: float
    w: float
    h: float
    puntaje: float = 1.0

    @property
    def area(self) -> float:
        return self.w * self.h


@dataclass(frozen=True)
class Recorte:
    """Va de (x0, y0) a (x1, y1), sin incluir x1 ni y1."""

    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def ancho(self) -> int:
        return self.x1 - self.x0

    @property
    def alto(self) -> int:
        return self.y1 - self.y0

    @property
    def vacio(self) -> bool:
        return self.ancho <= 0 or self.alto <= 0


def elegir_cara(caras: Sequence[Cara], cara_min: float) -> int | None:
    """Índice de la cara de mayor área entre las que miden al menos `cara_min` de alto; None si no queda ninguna.

    Con dos caras de la misma área gana la primera.
    """
    candidatas = [indice for indice, cara in enumerate(caras) if cara.h >= cara_min]
    if not candidatas:
        return None
    return max(candidatas, key=lambda indice: caras[indice].area)


def calcular_recorte(cara: Cara, ancho: int, alto: int) -> Recorte:
    """Fórmula del contrato: 25 % de margen, piso al inicio, techo al final y cortado en los bordes del cuadro."""
    return Recorte(
        x0=max(0, math.floor(cara.x - cara.w / 4)),
        y0=max(0, math.floor(cara.y - cara.h / 4)),
        x1=min(ancho, math.ceil(cara.x + cara.w + cara.w / 4)),
        y1=min(alto, math.ceil(cara.y + cara.h + cara.h / 4)),
    )
