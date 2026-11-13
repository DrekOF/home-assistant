"""
Nombre: huellas.py
Descripción: Rutas de las huellas de una persona: listar sus muestras sin la huella, borrarlas todas y borrar una (RF-12 · C1). Las huellas nunca salen por la API.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text

from accesia.api.personas import exigir_persona
from accesia.db import Conexion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import RostroResumen
from accesia.sesion import administrador_actual

registro = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Rostros"], dependencies=[Depends(administrador_actual)])


def _id_de_rostro(texto: str) -> UUID | None:
    """El id de la ruta; un texto que no es un uuid es una muestra que no existe (404), como en el resto de la API."""
    try:
        return UUID(texto)
    except ValueError:
        return None


@router.get("/personas/{persona_id}/rostros", response_model=list[RostroResumen], operation_id="listarRostros")
def listar_rostros(persona_id: str, conexion: Conexion) -> list[RostroResumen]:
    """Las muestras en el orden en que se guardaron, sin la huella."""
    persona = exigir_persona(conexion, persona_id)
    filas = conexion.execute(
        text("SELECT id, fuente, modelo, calidad, creado FROM rostro WHERE persona_id = :id ORDER BY creado, id"),
        {"id": persona.id},
    ).all()
    return [RostroResumen(**fila._mapping) for fila in filas]


@router.delete("/personas/{persona_id}/rostros", status_code=204, operation_id="borrarRostros")
def borrar_rostros(persona_id: str, conexion: Conexion) -> None:
    """RF-12 · C1: borra todas las huellas de la persona. Si no tenía, también responde 204."""
    persona = exigir_persona(conexion, persona_id)
    borradas = conexion.execute(text("DELETE FROM rostro WHERE persona_id = :id"), {"id": persona.id}).rowcount
    registro.info("Se borraron %d huellas de la persona %s (RF-12 · C1).", borradas, persona.id)


@router.delete("/rostros/{rostro_id}", status_code=204, operation_id="borrarRostro")
def borrar_rostro(rostro_id: str, conexion: Conexion) -> None:
    borrada = conexion.execute(
        text("DELETE FROM rostro WHERE id = :id RETURNING persona_id"), {"id": _id_de_rostro(rostro_id)}
    ).one_or_none()
    if borrada is None:
        raise ErrorAccesIA(404, "no_encontrado", "Esa muestra no existe o ya fue borrada.")
    registro.info("Se borró una huella de la persona %s (RF-12 · C1).", borrada.persona_id)
