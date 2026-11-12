"""
Nombre: inscripciones.py
Descripción: Rutas de las inscripciones: abrir, ver el avance y cancelar (RF-03 · C1, C5 y C6; R9).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response

from accesia import inscripciones
from accesia.db import Conexion
from accesia.errores import ErrorAccesIA, respuesta_error
from accesia.esquemas import Inscripcion, InscripcionNueva
from accesia.sesion import administrador_actual

router = APIRouter(prefix="/api/v1", tags=["Inscripciones"], dependencies=[Depends(administrador_actual)])


def _no_existe() -> ErrorAccesIA:
    return ErrorAccesIA(404, "no_encontrado", "Esa inscripción no existe.")


def _id(texto: str) -> UUID:
    """El id de la ruta; un texto que no es un uuid es una inscripción que no existe (404), como en el resto de la API."""
    try:
        return UUID(texto)
    except ValueError:
        raise _no_existe() from None


@router.post("/inscripciones", status_code=201, response_model=Inscripcion, operation_id="abrirInscripcion")
def abrir_inscripcion(datos: InscripcionNueva, conexion: Conexion) -> Inscripcion:
    return inscripciones.abrir(conexion, datos)


@router.get("/inscripciones/{inscripcion_id}", response_model=Inscripcion, operation_id="verInscripcion")
def ver_inscripcion(inscripcion_id: str, conexion: Conexion) -> Inscripcion:
    inscripcion = inscripciones.ver(conexion, _id(inscripcion_id))
    if inscripcion is None:
        raise _no_existe()
    return inscripcion


@router.delete("/inscripciones/{inscripcion_id}", status_code=204, operation_id="cancelarInscripcion")
def cancelar_inscripcion(inscripcion_id: str, conexion: Conexion) -> Response:
    resultado = inscripciones.cancelar(conexion, _id(inscripcion_id))
    if resultado == "no_existe":
        raise _no_existe()
    if resultado == "terminada":
        # Se responde sin lanzar la excepción: si se acaba de vencer, el vencimiento queda guardado.
        return respuesta_error(409, "inscripcion_terminada", "La inscripción ya terminó: no se puede cancelar.")
    return Response(status_code=204)
