"""
Nombre: tiempo.py
Descripción: Hora de Colombia para el servidor de AccesIA (R8).
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

from datetime import datetime

from accesia.config import configuracion


def ahora() -> datetime:
    """Hora actual en la zona de Colombia, sin microsegundos (2026-11-20T07:58:12-05:00)."""
    return datetime.now(configuracion().zona).replace(microsecond=0)
