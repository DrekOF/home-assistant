"""
Nombre: inscripciones.py
Descripción: Estado de las inscripciones (R9): vencer las que ya pasaron su hora y cancelar la activa de una persona. B2 suma el resto.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Connection, text


def vencer_inscripciones(conexion: Connection, ahora: datetime, dispositivo: str | None = None) -> int:
    """R9: las inscripciones activas cuya hora ya pasó quedan vencidas, con terminada igual a la hora en que vencieron.

    Se llama al listar o ver cámaras, y B2 la usa al abrir una inscripción y al llegar una cara. Sin dispositivo,
    revisa todas las cámaras. Devuelve cuántas venció.
    """
    filtro = "" if dispositivo is None else " AND dispositivo_codigo = :dispositivo"
    resultado = conexion.execute(
        text(
            "UPDATE inscripcion SET estado = 'vencida', terminada = vence "
            "WHERE estado = 'activa' AND vence <= :ahora" + filtro
        ),
        {"ahora": ahora, "dispositivo": dispositivo},
    )
    return resultado.rowcount


def cancelar_inscripcion_de(conexion: Connection, persona_id: UUID, ahora: datetime) -> int:
    """Cancela la inscripción activa de la persona (RF-02 · C5). Primero vence las que ya pasaron su hora."""
    vencer_inscripciones(conexion, ahora)
    resultado = conexion.execute(
        text(
            "UPDATE inscripcion SET estado = 'cancelada', terminada = :ahora "
            "WHERE persona_id = :persona_id AND estado = 'activa'"
        ),
        {"ahora": ahora, "persona_id": persona_id},
    )
    return resultado.rowcount
