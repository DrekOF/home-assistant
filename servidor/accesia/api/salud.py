"""
Nombre: salud.py
Descripción: GET /api/v1/salud: estado del servidor, la base de datos y MQTT (esquema Salud de openapi.yaml).
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from accesia import __version__
from accesia.db import base_disponible
from accesia.mqtt import ClienteMqttDeLaApp
from accesia.tiempo import ahora

router = APIRouter(prefix="/api/v1", tags=["Salud"])


class Salud(BaseModel):
    estado: Literal["ok", "degradado"]
    base: Literal["ok", "error"]
    mqtt: Literal["ok", "sin_conexion"]
    version: str
    hora: datetime


@router.get("/salud", response_model=Salud, operation_id="verSalud")
def ver_salud(cliente_mqtt: ClienteMqttDeLaApp) -> Salud:
    base = "ok" if base_disponible() else "error"
    mqtt = "ok" if cliente_mqtt.conectado else "sin_conexion"
    estado = "ok" if base == "ok" and mqtt == "ok" else "degradado"
    return Salud(estado=estado, base=base, mqtt=mqtt, version=__version__, hora=ahora())
