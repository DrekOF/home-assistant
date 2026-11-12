"""
Nombre: __init__.py
Descripción: Paquete del simulador de la cámara de AccesIA (frente A): hace lo mismo que la cámara con la webcam o con una carpeta de fotos.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from importlib.metadata import PackageNotFoundError, version

try:
    VERSION = version("simulador")
except PackageNotFoundError:  # corre sin instalar (por ejemplo, desde el código fuente)
    VERSION = "0.0.0"

# Cabecera X-AccesIA-Firmware del contrato (api-dispositivo.md · Petición).
FIRMWARE = f"simulador-{VERSION}"
