"""
Nombre: camaras.py
Descripción: Rutas de las cámaras: listar, crear, ver, editar y cambiar el token (RF-10 · C1 a C3). El envío de rostros es de B2.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from fastapi import APIRouter, Depends

from accesia import camaras
from accesia.db import Conexion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Dispositivo, DispositivoCambios, DispositivoConToken, DispositivoNuevo
from accesia.sesion import administrador_actual

router = APIRouter(prefix="/api/v1", tags=["Cámaras"], dependencies=[Depends(administrador_actual)])


def _no_existe(codigo: str) -> ErrorAccesIA:
    return ErrorAccesIA(404, "no_encontrado", f"No hay una cámara con el código {codigo}.")


@router.get("/dispositivos", response_model=list[Dispositivo], operation_id="listarCamaras")
def listar_camaras(conexion: Conexion) -> list[Dispositivo]:
    return camaras.listar(conexion)


@router.post("/dispositivos", status_code=201, response_model=DispositivoConToken, operation_id="crearCamara")
def crear_camara(datos: DispositivoNuevo, conexion: Conexion) -> DispositivoConToken:
    return camaras.crear(conexion, datos)


@router.get("/dispositivos/{codigo}", response_model=Dispositivo, operation_id="verCamara")
def ver_camara(codigo: str, conexion: Conexion) -> Dispositivo:
    dispositivo = camaras.ver(conexion, codigo)
    if dispositivo is None:
        raise _no_existe(codigo)
    return dispositivo


@router.patch("/dispositivos/{codigo}", response_model=Dispositivo, operation_id="editarCamara")
def editar_camara(codigo: str, cambios: DispositivoCambios, conexion: Conexion) -> Dispositivo:
    dispositivo = camaras.editar(conexion, codigo, cambios)
    if dispositivo is None:
        raise _no_existe(codigo)
    return dispositivo


@router.post("/dispositivos/{codigo}/token", response_model=DispositivoConToken, operation_id="cambiarTokenCamara")
def cambiar_token(codigo: str, conexion: Conexion) -> DispositivoConToken:
    dispositivo = camaras.cambiar_token(conexion, codigo)
    if dispositivo is None:
        raise _no_existe(codigo)
    return dispositivo
