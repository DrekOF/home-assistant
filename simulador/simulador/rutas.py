"""
Nombre: rutas.py
Descripción: Rutas del simulador: la raíz del repositorio, su carpeta datos/ (que Git ignora) y cómo se busca la carpeta de fotos.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path

# simulador/simulador/rutas.py → la raíz del repositorio está dos carpetas arriba del paquete.
RAIZ = Path(__file__).resolve().parents[2]

# Una sola carpeta datos/, en la raíz: modelos y fotos de prueba, compartida con el servidor (CLAUDE.md).
DATOS = RAIZ / "datos"
MODELOS = DATOS / "modelos"
PRUEBA = DATOS / "prueba"


def resolver_carpeta(ruta: Path) -> Path:
    """Busca una ruta relativa primero desde la carpeta actual y, si no existe, desde la raíz del repositorio.

    Así `uv run simulador carpeta datos/prueba` funciona igual desde la raíz y desde `simulador/`.
    """
    if ruta.is_absolute() or ruta.exists():
        return ruta
    desde_raiz = RAIZ / ruta
    return desde_raiz if desde_raiz.exists() else ruta
