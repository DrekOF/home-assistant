"""
Nombre: sesion.py
Descripción: Rutas de la sesión de la web: iniciarSesion, verSesion y cerrarSesion (openapi.yaml, RNF-02 · C2 y C5).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from fastapi import APIRouter, Response
from sqlalchemy import text

from accesia.db import Conexion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Administrador, Credenciales
from accesia.seguridad import clave_correcta
from accesia.sesion import AdministradorDeLaSesion, abrir_sesion, cerrar_sesion

router = APIRouter(prefix="/api/v1", tags=["Sesión"])


@router.post("/sesion", response_model=Administrador, operation_id="iniciarSesion")
def iniciar_sesion(credenciales: Credenciales, respuesta: Response, conexion: Conexion) -> Administrador:
    fila = conexion.execute(
        text("SELECT id, correo, nombre, clave_hash, activo FROM administrador WHERE lower(correo) = lower(:correo)"),
        {"correo": credenciales.correo},
    ).one_or_none()
    correcta = clave_correcta(fila.clave_hash if fila else None, credenciales.clave)
    # Correo que no existe, clave equivocada o administrador inactivo: la misma respuesta, sin decir cuál.
    if fila is None or not correcta or not fila.activo:
        raise ErrorAccesIA(
            401, "credenciales_invalidas", "El correo o la clave no coinciden. Revísalos e intenta de nuevo."
        )
    abrir_sesion(respuesta, fila.id)
    return Administrador(id=fila.id, correo=fila.correo, nombre=fila.nombre)


@router.get("/sesion", response_model=Administrador, operation_id="verSesion")
def ver_sesion(administrador: AdministradorDeLaSesion) -> Administrador:
    return administrador


@router.delete("/sesion", status_code=204, operation_id="cerrarSesion")
def cerrar(respuesta: Response) -> None:
    # Siempre 204, haya sesión o no, como el simulacro de la web: cerrar dos veces no es un error.
    cerrar_sesion(respuesta)
