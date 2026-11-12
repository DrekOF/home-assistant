"""
Nombre: tiempo.py
Descripción: Hora de Colombia para el servidor de AccesIA (R8).
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

from datetime import datetime

from accesia.config import configuracion


def ahora() -> datetime:
    """Hora actual en la zona de Colombia, sin microsegundos (2026-11-20T07:58:12-05:00).

    Es la fuente de hora de lo que el servidor guarda y compara, para que las pruebas puedan fijarla.
    """
    return datetime.now(configuracion().zona).replace(microsecond=0)


def a_colombia(valor: datetime) -> datetime:
    """La misma hora en la zona de Colombia y sin microsegundos, como la muestra la API (R8)."""
    return valor.astimezone(configuracion().zona).replace(microsecond=0)
