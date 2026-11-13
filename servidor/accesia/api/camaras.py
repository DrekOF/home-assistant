"""
Nombre: camaras.py
Descripción: Rutas de las cámaras: listar, crear, ver, editar y cambiar el token (RF-10 · C1 a C3), con su disponibilidad y su estado de MQTT. Crear o editar publica su descubrimiento (RF-07 · C1). El envío de rostros está en rostros.py.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from accesia import camaras
from accesia.db import Conexion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Dispositivo, DispositivoCambios, DispositivoConToken, DispositivoNuevo
from accesia.mqtt import ClienteMqttDeLaApp
from accesia.sesion import administrador_actual

router = APIRouter(prefix="/api/v1", tags=["Cámaras"], dependencies=[Depends(administrador_actual)])


def _no_existe(codigo: str) -> ErrorAccesIA:
    return ErrorAccesIA(404, "no_encontrado", f"No hay una cámara con el código {codigo}.")


@router.get("/dispositivos", response_model=list[Dispositivo], operation_id="listarCamaras")
def listar_camaras(conexion: Conexion, mqtt: ClienteMqttDeLaApp) -> list[Dispositivo]:
    return camaras.listar(conexion, mqtt)


@router.post("/dispositivos", status_code=201, response_model=DispositivoConToken, operation_id="crearCamara")
def crear_camara(
    datos: DispositivoNuevo, conexion: Conexion, mqtt: ClienteMqttDeLaApp, tareas: BackgroundTasks
) -> DispositivoConToken:
    camara = camaras.crear(conexion, datos, mqtt)
    # Después de confirmar: el descubrimiento lee la cámara de la base (mqtt.md, Temas).
    tareas.add_task(mqtt.publicar_descubrimiento, camara.codigo)
    return camara


@router.get("/dispositivos/{codigo}", response_model=Dispositivo, operation_id="verCamara")
def ver_camara(codigo: str, conexion: Conexion, mqtt: ClienteMqttDeLaApp) -> Dispositivo:
    dispositivo = camaras.ver(conexion, codigo, mqtt)
    if dispositivo is None:
        raise _no_existe(codigo)
    return dispositivo


@router.patch("/dispositivos/{codigo}", response_model=Dispositivo, operation_id="editarCamara")
def editar_camara(
    codigo: str, cambios: DispositivoCambios, conexion: Conexion, mqtt: ClienteMqttDeLaApp, tareas: BackgroundTasks
) -> Dispositivo:
    dispositivo = camaras.editar(conexion, codigo, cambios, mqtt)
    if dispositivo is None:
        raise _no_existe(codigo)
    tareas.add_task(mqtt.publicar_descubrimiento, codigo)  # el nombre del dispositivo pudo cambiar
    return dispositivo


@router.post("/dispositivos/{codigo}/token", response_model=DispositivoConToken, operation_id="cambiarTokenCamara")
def cambiar_token(codigo: str, conexion: Conexion, mqtt: ClienteMqttDeLaApp) -> DispositivoConToken:
    dispositivo = camaras.cambiar_token(conexion, codigo, mqtt)
    if dispositivo is None:
        raise _no_existe(codigo)
    return dispositivo
