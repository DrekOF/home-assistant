"""
Nombre: main.py
Descripción: Aplicación FastAPI del servidor de AccesIA. Uvicorn la corre con un solo proceso.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

from fastapi import FastAPI

from accesia import __version__
from accesia.api import salud
from accesia.errores import registrar_manejadores


def crear_app() -> FastAPI:
    """Crea la aplicación. El contrato de la API es specs/contratos/openapi.yaml, así que no se publica otro."""
    app = FastAPI(
        title="API de AccesIA",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    registrar_manejadores(app)
    app.include_router(salud.router)
    return app


app = crear_app()
