"""
Nombre: resumen.py
Descripción: El mensaje Resumen de mqtt.md: la asistencia del día (R5) y los desconocidos de hoy, en la fecha local de Colombia (R8).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from datetime import datetime, time, timedelta

from sqlalchemy import Connection, text

from accesia.config import configuracion
from accesia.tiempo import a_colombia

POR_ESTADO = "SELECT estado, count(*) AS cuantos FROM asistencia WHERE fecha = :fecha GROUP BY estado"

DESCONOCIDOS = """
SELECT count(*) FROM evento_acceso
WHERE resultado = 'desconocido' AND fecha_hora >= :inicio AND fecha_hora < :fin
"""

# La última llegada es la de hora más reciente del día, aunque se haya registrado a mano antes que otra.
ULTIMA_LLEGADA = """
SELECT p.nombre, a.llegada
FROM asistencia a
JOIN persona p ON p.id = a.persona_id
WHERE a.fecha = :fecha
ORDER BY a.llegada DESC, a.id DESC
LIMIT 1
"""


def resumen(conexion: Connection, momento: datetime) -> dict:
    """El Resumen del día de ese momento. ultima_llegada es null si nadie ha llegado."""
    local = a_colombia(momento)
    fecha = local.date()
    inicio = datetime.combine(fecha, time.min, tzinfo=configuracion().zona)
    conteos = {fila.estado: fila.cuantos for fila in conexion.execute(text(POR_ESTADO), {"fecha": fecha})}
    desconocidos = conexion.execute(
        text(DESCONOCIDOS), {"inicio": inicio, "fin": inicio + timedelta(days=1)}
    ).scalar_one()
    ultima = conexion.execute(text(ULTIMA_LLEGADA), {"fecha": fecha}).one_or_none()
    a_tiempo, tarde, sin_horario = (conteos.get(estado, 0) for estado in ("a_tiempo", "tarde", "sin_horario"))
    return {
        "fecha": fecha.isoformat(),
        "asistentes": a_tiempo + tarde + sin_horario,
        "a_tiempo": a_tiempo,
        "tarde": tarde,
        "sin_horario": sin_horario,
        "desconocidos_hoy": desconocidos,
        "ultima_llegada": None
        if ultima is None
        else {"nombre": ultima.nombre, "hora": a_colombia(ultima.llegada).isoformat()},
        "hora": local.isoformat(),
    }
