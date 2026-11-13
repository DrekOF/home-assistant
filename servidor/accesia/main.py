"""
Nombre: main.py
Descripción: Aplicación FastAPI del servidor de AccesIA. Uvicorn la corre con un solo proceso; al arrancar exige SESION_SECRETO, crea el primer administrador, carga los modelos de cara y se conecta a MQTT sin esperar al broker.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.4
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from accesia import __version__
from accesia.alertas import ControlDeAlertas
from accesia.api import (
    accesos,
    asistencia,
    camaras,
    configuracion as rutas_configuracion,
    consentimiento,
    horarios,
    huellas,
    inscripciones,
    personas,
    rostros,
    salud,
    sesion,
)
from accesia.config import configuracion
from accesia.db import transaccion
from accesia.errores import registrar_manejadores
from accesia.mqtt import ClienteMqtt, resumen_periodico
from accesia.registro import configurar_registro
from accesia.rostros import ControlDeRitmo
from accesia.sesion import crear_primer_administrador
from accesia.vision import cargar_vision

registro = logging.getLogger(__name__)


def preparar_arranque() -> None:
    """Sin SESION_SECRETO el servidor no arranca. Si falta el primer administrador, lo crea."""
    conf = configuracion()
    if conf.sesion_secreto is None or not conf.sesion_secreto.get_secret_value():
        raise RuntimeError("Falta SESION_SECRETO en infra/.env: el servidor no arranca sin ella.")
    clave = conf.admin_clave_inicial.get_secret_value() if conf.admin_clave_inicial else None
    try:
        with transaccion() as conexion:
            crear_primer_administrador(conexion, conf.admin_correo, clave)
    except SQLAlchemyError:
        # La API sigue arriba (salud dirá base: error); el administrador se crea en el próximo arranque.
        registro.exception("No se pudo revisar el primer administrador: la base no respondió.")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    await run_in_threadpool(preparar_arranque)
    # YuNet y SFace se cargan una sola vez. Sin los modelos, el servidor no arranca.
    app.state.vision = await run_in_threadpool(cargar_vision)
    # MQTT: si el broker no responde, el servidor arranca igual y paho reintenta solo (mqtt.md, B2 del Día 3).
    cliente = ClienteMqtt(configuracion().mqtt_url)
    app.state.mqtt = cliente
    cliente.iniciar()
    periodico = asyncio.create_task(resumen_periodico(cliente))
    try:
        yield
    finally:
        periodico.cancel()
        await run_in_threadpool(cliente.detener)


def crear_app() -> FastAPI:
    """Crea la aplicación. El contrato de la API es specs/contratos/openapi.yaml, así que no se publica otro."""
    configurar_registro()
    app = FastAPI(
        title="API de AccesIA",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=ciclo_de_vida,
    )
    registrar_manejadores(app)
    # El 429, la última alerta de R6 y la conexión MQTT viven en memoria: el servidor corre con un solo proceso
    # (arquitectura.md). Hasta que arranca, el cliente MQTT no tiene URL y no publica nada.
    app.state.ritmo = ControlDeRitmo()
    app.state.alertas = ControlDeAlertas()
    app.state.mqtt = ClienteMqtt(None)
    for rutas in (
        salud,
        sesion,
        personas,
        consentimiento,
        horarios,
        camaras,
        rostros,
        inscripciones,
        huellas,
        accesos,
        asistencia,
        rutas_configuracion,
    ):
        app.include_router(rutas.router)
    return app


app = crear_app()
