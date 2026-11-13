"""
Nombre: asistencia.py
Descripción: Asistencia con R5 y R8: califica una llegada con el bloque del horario de la persona y registra la primera llegada del día. La usan la cámara, el registro manual y la semilla del agente (RF-06 · C1, C2 y C5).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import Connection, text

from accesia.esquemas import EstadoAsistencia, OrigenAsistencia
from accesia.tiempo import a_colombia

UN_MINUTO = timedelta(minutes=1)

BLOQUE_DEL_DIA = """
SELECT b.hora_inicio, b.tolerancia_min
FROM persona p
JOIN horario_bloque b ON b.horario_id = p.horario_id AND b.dia = :dia
WHERE p.id = :persona_id
"""

# La restricción UNIQUE (persona_id, fecha) decide cuál es la primera llegada: si ya hay una ese día, no se escribe
# nada. Con dos registros a la vez, PostgreSQL hace esperar al segundo hasta que el primero termina, y el segundo
# tampoco escribe; como no hay error, la transacción sigue sana sin un savepoint.
INSERTAR = """
INSERT INTO asistencia (persona_id, fecha, llegada, estado, minutos_tarde, origen, evento_id, registrado_por)
VALUES (:persona_id, :fecha, :llegada, :estado, :minutos_tarde, :origen, :evento_id, :registrado_por)
ON CONFLICT (persona_id, fecha) DO NOTHING
RETURNING id
"""


@dataclass(frozen=True)
class Bloque:
    """La hora de entrada de un día del horario (D-20)."""

    hora_inicio: time
    tolerancia_min: int


@dataclass(frozen=True)
class Calificacion:
    estado: EstadoAsistencia
    minutos_tarde: int | None  # solo con tarde


@dataclass(frozen=True)
class Llegada:
    """Una llegada recién creada. B2 publica estado y minutos_tarde en el campo asistencia del Evento (mqtt.md)."""

    id: UUID
    persona_id: UUID
    fecha: date
    llegada: datetime
    estado: EstadoAsistencia
    minutos_tarde: int | None
    origen: OrigenAsistencia


def fecha_local(momento: datetime) -> date:
    """R8: la fecha de la asistencia es la fecha local de Colombia (2026-11-21T03:30:00Z es el 20)."""
    return a_colombia(momento).date()


def calificar_llegada(llegada: datetime, bloque: Bloque | None) -> Calificacion:
    """R5: a_tiempo hasta el inicio del bloque más su tolerancia, incluido; después, tarde, con los minutos completos
    desde el inicio. Sin bloque ese día, sin_horario. Compara con segundos, en la hora y la fecha de Colombia."""
    if bloque is None:
        return Calificacion("sin_horario", None)
    local = a_colombia(llegada)
    inicio = datetime.combine(local.date(), bloque.hora_inicio, tzinfo=local.tzinfo)
    if local <= inicio + timedelta(minutes=bloque.tolerancia_min):
        return Calificacion("a_tiempo", None)
    return Calificacion("tarde", (local - inicio) // UN_MINUTO)


def bloque_del_dia(conexion: Connection, persona_id: UUID, fecha: date) -> Bloque | None:
    """El bloque del horario de la persona para el día de la semana de la fecha (1 = lunes … 7 = domingo, D-20)."""
    fila = conexion.execute(
        text(BLOQUE_DEL_DIA), {"persona_id": persona_id, "dia": fecha.isoweekday()}
    ).one_or_none()
    return None if fila is None else Bloque(hora_inicio=fila.hora_inicio, tolerancia_min=fila.tolerancia_min)


def registrar_llegada(
    conexion: Connection,
    persona_id: UUID,
    momento: datetime,
    origen: OrigenAsistencia,
    evento_id: UUID | None = None,
    registrado_por: UUID | None = None,
) -> Llegada | None:
    """R5: guarda la llegada si es la primera del día (fecha local, R8) y la devuelve calificada.

    Si la persona ya tenía llegada ese día, no cambia nada y devuelve None: cuenta la primera, venga de la cámara o
    sea manual. La llegada se guarda sin microsegundos, como ahora().
    """
    llegada = a_colombia(momento)
    fecha = llegada.date()
    calificacion = calificar_llegada(llegada, bloque_del_dia(conexion, persona_id, fecha))
    creada = conexion.execute(
        text(INSERTAR),
        {
            "persona_id": persona_id,
            "fecha": fecha,
            "llegada": llegada,
            "estado": calificacion.estado,
            "minutos_tarde": calificacion.minutos_tarde,
            "origen": origen,
            "evento_id": evento_id,
            "registrado_por": registrado_por,
        },
    ).scalar_one_or_none()
    if creada is None:
        return None
    return Llegada(
        id=creada,
        persona_id=persona_id,
        fecha=fecha,
        llegada=llegada,
        estado=calificacion.estado,
        minutos_tarde=calificacion.minutos_tarde,
        origen=origen,
    )
