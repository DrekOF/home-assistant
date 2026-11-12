"""
Nombre: armar.py
Descripción: Arma datos directamente en la base para las pruebas del servidor: personas, consentimientos, cámaras, inscripciones, huellas, eventos y asistencia.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import math
from datetime import datetime
from uuid import UUID

from sqlalchemy import Connection, text

# Una huella de prueba: 128 números iguales, con norma 1, como las de SFace.
HUELLA = "[" + ",".join([f"{1 / math.sqrt(128):.8f}"] * 128) + "]"


def persona(conexion: Connection, documento: str = "1075000001", nombre: str = "Ana María Gómez", **campos) -> UUID:
    valores = {"documento": documento, "nombre": nombre, "rol": "estudiante", "horario_id": None, "activa": True}
    valores.update(campos)
    return conexion.execute(
        text(
            "INSERT INTO persona (documento, nombre, rol, horario_id, activa) "
            "VALUES (:documento, :nombre, :rol, :horario_id, :activa) RETURNING id"
        ),
        valores,
    ).scalar_one()


def consentimiento(conexion: Connection, persona_id: UUID) -> UUID:
    return conexion.execute(
        text("INSERT INTO consentimiento (persona_id, version_texto) VALUES (:persona_id, '1.0') RETURNING id"),
        {"persona_id": persona_id},
    ).scalar_one()


def camara(
    conexion: Connection, codigo: str = "entrada", tipo: str = "simulador", ultimo_contacto: datetime | None = None
) -> str:
    conexion.execute(
        text(
            "INSERT INTO dispositivo (codigo, nombre, tipo, token_hash, ultimo_contacto) "
            "VALUES (:codigo, :nombre, :tipo, :token_hash, :ultimo_contacto)"
        ),
        {
            "codigo": codigo,
            "nombre": codigo.capitalize(),
            "tipo": tipo,
            "token_hash": "0" * 64,
            "ultimo_contacto": ultimo_contacto,
        },
    )
    return codigo


def inscripcion(
    conexion: Connection, persona_id: UUID, dispositivo: str, vence: datetime, muestras: int = 0, requeridas: int = 5
) -> UUID:
    return conexion.execute(
        text(
            "INSERT INTO inscripcion (persona_id, dispositivo_codigo, requeridas, muestras, vence) "
            "VALUES (:persona_id, :dispositivo, :requeridas, :muestras, :vence) RETURNING id"
        ),
        {
            "persona_id": persona_id,
            "dispositivo": dispositivo,
            "requeridas": requeridas,
            "muestras": muestras,
            "vence": vence,
        },
    ).scalar_one()


def rostro(conexion: Connection, persona_id: UUID, inscripcion_id: UUID | None = None) -> UUID:
    return conexion.execute(
        text(
            "INSERT INTO rostro (persona_id, inscripcion_id, huella, fuente) "
            "VALUES (:persona_id, :inscripcion_id, CAST(:huella AS vector), 'simulador') RETURNING id"
        ),
        {"persona_id": persona_id, "inscripcion_id": inscripcion_id, "huella": HUELLA},
    ).scalar_one()


def evento(conexion: Connection, dispositivo: str, persona_id: UUID) -> UUID:
    return conexion.execute(
        text(
            "INSERT INTO evento_acceso (dispositivo_codigo, persona_id, resultado, similitud) "
            "VALUES (:dispositivo, :persona_id, 'permitido', 0.71) RETURNING id"
        ),
        {"dispositivo": dispositivo, "persona_id": persona_id},
    ).scalar_one()


def asistencia(conexion: Connection, persona_id: UUID) -> UUID:
    return conexion.execute(
        text(
            "INSERT INTO asistencia (persona_id, fecha, llegada, estado) "
            "VALUES (:persona_id, current_date, now(), 'a_tiempo') RETURNING id"
        ),
        {"persona_id": persona_id},
    ).scalar_one()


def contar(conexion: Connection, tabla: str, persona_id: UUID) -> int:
    """Filas de una tabla de la lista cerrada que pertenecen a la persona."""
    assert tabla in {"consentimiento", "inscripcion", "rostro", "asistencia"}
    return conexion.execute(
        text(f"SELECT count(*) FROM {tabla} WHERE persona_id = :persona_id"), {"persona_id": persona_id}
    ).scalar_one()
