"""
Nombre: hora_fija.py
Descripción: Hora fija para las pruebas del agente y de su semilla: el viernes 20 de noviembre de 2026 a las 10:00 en Colombia, en todos los módulos del servidor.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

# Hoy es el viernes 2026-11-20 a las 10:00; ayer, el 19, y antier, el 18 (mcp-agente.md, Evaluación).
HOY = datetime(2026, 11, 20, 10, 0, tzinfo=ZoneInfo("America/Bogota"))


@contextmanager
def ahora_fijo(momento: datetime = HOY) -> Iterator[None]:
    """Fija accesia.tiempo.ahora() en todos los módulos del servidor ya importados, también los que la importaron
    con from … import ahora. Sirve fuera de una prueba, por ejemplo en una fixture de módulo."""
    import accesia.main  # noqa: F401 — importa todo el servidor antes de reemplazar la hora
    from accesia import tiempo

    original = tiempo.ahora
    with pytest.MonkeyPatch.context() as parche:
        for nombre, modulo in list(sys.modules.items()):
            if (nombre == "accesia" or nombre.startswith("accesia.")) and getattr(modulo, "ahora", None) is original:
                parche.setattr(modulo, "ahora", lambda: momento)
        yield
