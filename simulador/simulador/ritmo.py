"""
Nombre: ritmo.py
Descripción: Esperas entre recortes, contadas desde que llega la respuesta (specs/contratos/api-dispositivo.md, Qué hace la cámara con la respuesta).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import math
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from simulador.envio import Respuesta

# Tras estos resultados la cámara muestra el mensaje y espera 3 s.
RESULTADOS_DE_DECISION = frozenset({"permitido", "denegado", "desconocido"})
ESPERA_MINIMA_S = 1.0
ESPERA_DECISION_S = 3.0
ESPERA_TOKEN_S = 30.0
# Sin respuesta en 5 s, o 5xx: 1, 2, 4, 8 y después 10 s cada vez, hasta que llegue otra respuesta.
ESPERAS_FALLA_S = (1.0, 2.0, 4.0, 8.0, 10.0)


def es_falla(respuesta: Respuesta) -> bool:
    return respuesta.estado is None or respuesta.estado >= 500


def leer_retry_after(valor: str | None, ahora: datetime | None = None) -> float:
    """Segundos de Retry-After, en número o en fecha HTTP.

    Nunca menos de 1 s: es la espera mínima tras cualquier respuesta.
    """
    if valor is None:
        return ESPERA_MINIMA_S
    try:
        segundos = float(valor)
    except ValueError:
        try:
            fecha = parsedate_to_datetime(valor)
        except (TypeError, ValueError):
            return ESPERA_MINIMA_S
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=UTC)
        segundos = (fecha - (ahora or datetime.now(UTC))).total_seconds()
    if not math.isfinite(segundos):
        return ESPERA_MINIMA_S
    return max(ESPERA_MINIMA_S, segundos)


def espera_tras(respuesta: Respuesta, fallas_previas: int = 0) -> float:
    """Segundos que se esperan, desde que llega la respuesta, antes de enviar el siguiente recorte."""
    if es_falla(respuesta):
        return ESPERAS_FALLA_S[min(fallas_previas, len(ESPERAS_FALLA_S) - 1)]
    if respuesta.estado == 200:
        return ESPERA_DECISION_S if respuesta.resultado in RESULTADOS_DE_DECISION else ESPERA_MINIMA_S
    if respuesta.estado in (401, 403):
        return ESPERA_TOKEN_S
    if respuesta.estado == 429:
        return leer_retry_after(respuesta.retry_after)
    # Otras respuestas (413, 415, 422…): la espera mínima de 1 s tras cada respuesta.
    return ESPERA_MINIMA_S


class Ritmo:
    """Dice cuándo se puede enviar otro recorte. El reloj se inyecta para probar sin esperar de verdad."""

    def __init__(self, reloj: Callable[[], float] = time.monotonic) -> None:
        self._reloj = reloj
        self._proximo = -math.inf
        self._fallas = 0
        self._candado = threading.Lock()

    def falta(self) -> float:
        """Segundos que faltan para poder enviar (0 si ya se puede)."""
        with self._candado:
            return max(0.0, self._proximo - self._reloj())

    def puede_enviar(self) -> bool:
        return self.falta() == 0.0

    def registrar(self, respuesta: Respuesta) -> float:
        """Se llama apenas llega la respuesta: la espera se cuenta desde ese momento, no desde el envío."""
        with self._candado:
            espera = espera_tras(respuesta, self._fallas)
            self._fallas = self._fallas + 1 if es_falla(respuesta) else 0
            self._proximo = self._reloj() + espera
            return espera
