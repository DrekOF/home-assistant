"""
Nombre: armar.py
Descripción: Arma datos directamente en la base para las pruebas del servidor: horarios con bloques, personas, consentimientos, cámaras, inscripciones, huellas, eventos y asistencia.
Fecha de creación: 2026-11-12
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.3
"""

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Connection, text

# Una huella de prueba: 128 números iguales, con norma 1, como las de SFace.
HUELLA = "[" + ",".join([f"{1 / math.sqrt(128):.8f}"] * 128) + "]"


def horario(conexion: Connection, nombre: str, *bloques: tuple[int, str, int]) -> UUID:
    """Un horario con sus bloques: (día de 1 = lunes a 7 = domingo, hora de inicio «HH:MM», tolerancia en minutos)."""
    horario_id = conexion.execute(
        text("INSERT INTO horario (nombre) VALUES (:nombre) RETURNING id"), {"nombre": nombre}
    ).scalar_one()
    for dia, hora_inicio, tolerancia_min in bloques:
        conexion.execute(
            text(
                "INSERT INTO horario_bloque (horario_id, dia, hora_inicio, tolerancia_min) "
                "VALUES (:horario_id, :dia, CAST(:hora_inicio AS time), :tolerancia_min)"
            ),
            {"horario_id": horario_id, "dia": dia, "hora_inicio": hora_inicio, "tolerancia_min": tolerancia_min},
        )
    return horario_id


def clase_ia(conexion: Connection) -> UUID:
    """El horario de ejemplo de R5 que trae el SQL del contrato: de lunes a viernes a las 07:00, con 10 min."""
    return conexion.execute(text("SELECT id FROM horario WHERE nombre = 'Clase IA'")).scalar_one()


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


def consentimiento(conexion: Connection, persona_id: UUID, aceptado_en: datetime | None = None) -> UUID:
    """Un consentimiento vigente; sin aceptado_en, con la hora de la base (now() de la transacción)."""
    if aceptado_en is None:
        return conexion.execute(
            text("INSERT INTO consentimiento (persona_id, version_texto) VALUES (:persona_id, '1.0') RETURNING id"),
            {"persona_id": persona_id},
        ).scalar_one()
    return conexion.execute(
        text(
            "INSERT INTO consentimiento (persona_id, version_texto, aceptado_en) "
            "VALUES (:persona_id, '1.0', :aceptado_en) RETURNING id"
        ),
        {"persona_id": persona_id, "aceptado_en": aceptado_en},
    ).scalar_one()


def camara(
    conexion: Connection,
    codigo: str = "entrada",
    tipo: str = "simulador",
    ultimo_contacto: datetime | None = None,
    token_hash: str = "0" * 64,
    activo: bool = True,
    url_captura: str | None = None,
) -> str:
    """Una cámara. Las de tipo respaldo necesitan su URL de captura (la base lo exige)."""
    conexion.execute(
        text(
            "INSERT INTO dispositivo (codigo, nombre, tipo, token_hash, ultimo_contacto, activo, url_captura) "
            "VALUES (:codigo, :nombre, :tipo, :token_hash, :ultimo_contacto, :activo, :url_captura)"
        ),
        {
            "codigo": codigo,
            "nombre": codigo.capitalize(),
            "tipo": tipo,
            "token_hash": token_hash,
            "ultimo_contacto": ultimo_contacto,
            "activo": activo,
            "url_captura": url_captura,
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


def rostro(
    conexion: Connection,
    persona_id: UUID,
    inscripcion_id: UUID | None = None,
    huella: Sequence[float] | None = None,
    calidad: float | None = None,
    creado: datetime | None = None,
) -> UUID:
    """Una huella de la persona; sin huella, la de prueba (HUELLA). Sin creado, con now() de la transacción."""
    texto = HUELLA if huella is None else "[" + ",".join(format(float(valor), ".9g") for valor in huella) + "]"
    return conexion.execute(
        text(
            "INSERT INTO rostro (persona_id, inscripcion_id, huella, fuente, calidad, creado) "
            "VALUES (:persona_id, :inscripcion_id, CAST(:huella AS vector), 'simulador', :calidad, "
            "COALESCE(CAST(:creado AS timestamptz), now())) RETURNING id"
        ),
        {
            "persona_id": persona_id,
            "inscripcion_id": inscripcion_id,
            "huella": texto,
            "calidad": calidad,
            "creado": creado,
        },
    ).scalar_one()


def evento(
    conexion: Connection,
    dispositivo: str,
    persona_id: UUID | None,
    resultado: str = "permitido",
    motivo: str | None = None,
    similitud: float | None = 0.71,
    fecha_hora: datetime | None = None,
) -> UUID:
    """Un evento de acceso; sin fecha_hora, con now() de la transacción."""
    return conexion.execute(
        text(
            "INSERT INTO evento_acceso (fecha_hora, dispositivo_codigo, persona_id, resultado, motivo, similitud) "
            "VALUES (COALESCE(CAST(:fecha_hora AS timestamptz), now()), :dispositivo, :persona_id, :resultado, "
            ":motivo, :similitud) RETURNING id"
        ),
        {
            "fecha_hora": fecha_hora,
            "dispositivo": dispositivo,
            "persona_id": persona_id,
            "resultado": resultado,
            "motivo": motivo,
            "similitud": similitud,
        },
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


def inscrita(
    conexion: Connection,
    nombre: str,
    documento: str,
    *huellas: Sequence[float],
    activa: bool = True,
    con_consentimiento: bool = True,
    horario_id: UUID | None = None,
) -> UUID:
    """Una persona con sus huellas ya guardadas, su horario y, si se pide, con consentimiento vigente."""
    persona_id = persona(conexion, documento=documento, nombre=nombre, activa=activa, horario_id=horario_id)
    if con_consentimiento:
        # Una hora antes: revocar por la API usa ahora() sin microsegundos y no puede quedar antes de aceptado_en.
        consentimiento(conexion, persona_id, aceptado_en=datetime.now(UTC) - timedelta(hours=1))
    for huella in huellas:
        rostro(conexion, persona_id, huella=huella)
    return persona_id


def eventos(conexion: Connection) -> list:
    """Los eventos de acceso guardados, del más antiguo al más reciente."""
    return conexion.execute(
        text(
            "SELECT id, fecha_hora, dispositivo_codigo, persona_id, resultado, motivo, similitud "
            "FROM evento_acceso ORDER BY fecha_hora, id"
        )
    ).all()


def llegadas(conexion: Connection) -> list:
    """Las llegadas guardadas (tabla asistencia), por fecha y hora de llegada."""
    return conexion.execute(
        text(
            "SELECT id, persona_id, fecha, llegada, estado, minutos_tarde, origen, evento_id, registrado_por "
            "FROM asistencia ORDER BY fecha, llegada, id"
        )
    ).all()
