"""
Nombre: registro.py
Descripción: Registro (logging) del servidor de AccesIA: los avisos INFO del paquete accesia salen por la salida de errores, con la hora de Colombia, y así se ven en el registro del contenedor.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Uvicorn solo configura sus propios registros. Sin esto, los avisos de accesia caen en el manejador de reserva de
Python, que solo deja pasar WARNING o más: por eso no se veía, por ejemplo, que se creó el primer administrador.
Nunca se registran imágenes ni su base64, ni a quién se parece una cara (RNF-01).
"""

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

FORMATO = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class _HoraDeColombia(logging.Formatter):
    """La hora de cada línea en ISO 8601 con zona, como el resto del sistema (R8): 2026-11-20T07:58:12-05:00."""

    def __init__(self, zona: ZoneInfo) -> None:
        super().__init__(FORMATO)
        self._zona = zona

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802 (nombre de logging)
        return datetime.fromtimestamp(record.created, self._zona).isoformat(timespec="seconds")


class _SalidaDeErrores(logging.StreamHandler):
    """Escribe en el sys.stderr de cada momento, no en el que había al crearlo (como el manejador de reserva)."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def stream(self):  # type: ignore[override]
        return sys.stderr

    @stream.setter
    def stream(self, _valor) -> None:
        pass


def _zona() -> ZoneInfo:
    try:
        from accesia.config import configuracion

        return configuracion().zona
    except Exception:  # sin configuración todavía (por ejemplo, falta DATABASE_URL): la hora de Colombia igual
        return ZoneInfo("America/Bogota")


def configurar_registro() -> None:
    """Deja el registro accesia en INFO con un manejador propio. Se puede llamar varias veces: solo agrega uno."""
    registro = logging.getLogger("accesia")
    registro.setLevel(logging.INFO)
    if any(isinstance(manejador, _SalidaDeErrores) for manejador in registro.handlers):
        return
    manejador = _SalidaDeErrores()
    manejador.setFormatter(_HoraDeColombia(_zona()))
    registro.addHandler(manejador)
