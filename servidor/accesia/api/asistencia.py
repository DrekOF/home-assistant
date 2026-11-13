"""
Nombre: asistencia.py
Descripción: Rutas de asistencia (R5): el reporte de un día, el registro manual de una llegada, las llegadas de una persona y la exportación a CSV (RF-06 · C3, C4 y C5; RF-12 · C3).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy import Row, text

from accesia.api.personas import buscar_persona, exigir_persona, no_existe
from accesia.asistencia import fecha_local, registrar_llegada
from accesia.db import Conexion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Asistencia, AsistenciaManualNueva, FilaAsistencia, PersonaCorta, ReporteAsistencia
from accesia.sesion import AdministradorDeLaSesion, administrador_actual
from accesia.tiempo import a_colombia, ahora

router = APIRouter(prefix="/api/v1", tags=["Asistencia"], dependencies=[Depends(administrador_actual)])

CONSULTA = """
SELECT a.id, a.fecha, a.llegada, a.estado, a.minutos_tarde, a.origen,
       p.id AS persona_id, p.nombre AS persona_nombre, ad.nombre AS registrado_por
FROM asistencia a
JOIN persona p ON p.id = a.persona_id
LEFT JOIN administrador ad ON ad.id = a.registrado_por
"""

# R5 · ausentes: personas activas cuyo horario tiene bloque ese día y sin llegada. Se calcula con el horario y el
# estado que la persona tiene hoy: la base no guarda su historia.
AUSENTES = """
SELECT p.id, p.nombre
FROM persona p
JOIN horario_bloque b ON b.horario_id = p.horario_id AND b.dia = :dia
WHERE p.activa
  AND NOT EXISTS (SELECT 1 FROM asistencia a WHERE a.persona_id = p.id AND a.fecha = :fecha)
ORDER BY p.nombre COLLATE "es-x-icu", p.id
"""

EXPORTAR = """
SELECT a.fecha, p.nombre, p.documento, a.llegada, a.estado, a.minutos_tarde, a.origen
FROM asistencia a
JOIN persona p ON p.id = a.persona_id
WHERE a.fecha BETWEEN :desde AND :hasta
ORDER BY a.fecha, a.llegada, p.nombre COLLATE "es-x-icu", a.id
"""

COLUMNAS_CSV = ("fecha", "nombre", "documento", "llegada", "estado", "minutos_tarde", "origen")

# Una celda que empieza así es una fórmula para Excel o LibreOffice: se le antepone ' para que quede como texto.
INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _fila(fila: Row) -> dict:
    return {
        "persona": PersonaCorta(id=fila.persona_id, nombre=fila.persona_nombre),
        "llegada": fila.llegada,
        "estado": fila.estado,
        "minutos_tarde": fila.minutos_tarde,
        "origen": fila.origen,
        "registrado_por": fila.registrado_por,
    }


def _exigir_rango(desde: date | None, hasta: date | None) -> None:
    if desde is not None and hasta is not None and desde > hasta:
        raise ErrorAccesIA(422, "validacion", "La fecha «desde» no puede ser posterior a «hasta».")


def _celda(texto: str) -> str:
    return "'" + texto if texto.startswith(INICIO_DE_FORMULA) else texto


@router.get("/asistencia", response_model=ReporteAsistencia, operation_id="verAsistencia")
def ver_asistencia(conexion: Conexion, fecha: date | None = None) -> ReporteAsistencia:
    """El reporte de una fecha local de Colombia; sin fecha, el de hoy (R8). Las listas van por hora de llegada."""
    dia = fecha if fecha is not None else fecha_local(ahora())
    filas = conexion.execute(
        text(CONSULTA + ' WHERE a.fecha = :fecha ORDER BY a.llegada, p.nombre COLLATE "es-x-icu", a.id'),
        {"fecha": dia},
    ).all()
    por_estado: dict[str, list[FilaAsistencia]] = {"a_tiempo": [], "tarde": [], "sin_horario": []}
    for fila in filas:
        por_estado[fila.estado].append(FilaAsistencia(**_fila(fila)))
    ausentes = conexion.execute(text(AUSENTES), {"fecha": dia, "dia": dia.isoweekday()}).all()
    return ReporteAsistencia(
        fecha=dia,
        a_tiempo=por_estado["a_tiempo"],
        tarde=por_estado["tarde"],
        sin_horario=por_estado["sin_horario"],
        ausentes=[PersonaCorta(id=fila.id, nombre=fila.nombre) for fila in ausentes],
        total_llegadas=len(filas),
    )


@router.post("/asistencia", status_code=201, response_model=Asistencia, operation_id="registrarAsistenciaManual")
def registrar_asistencia_manual(
    datos: AsistenciaManualNueva, administrador: AdministradorDeLaSesion, conexion: Conexion
) -> Asistencia:
    """RF-06 · C5: R5 a la hora dada, en su fecha local. También para una persona inactiva: R5 no lo impide."""
    persona = buscar_persona(conexion, datos.persona_id)
    if persona is None:
        raise no_existe()
    if a_colombia(datos.llegada) > ahora():
        raise ErrorAccesIA(422, "validacion", "La hora de llegada no puede ser futura.")
    llegada = registrar_llegada(conexion, persona.id, datos.llegada, "manual", registrado_por=administrador.id)
    if llegada is None:
        raise ErrorAccesIA(
            409,
            "asistencia_duplicada",
            f"{persona.nombre} ya tiene llegada el {fecha_local(datos.llegada):%d/%m/%Y}: cuenta la primera del día.",
        )
    fila = conexion.execute(text(CONSULTA + " WHERE a.id = :id"), {"id": llegada.id}).one()
    return Asistencia(**_fila(fila), fecha=fila.fecha)


@router.get(
    "/personas/{persona_id}/asistencia", response_model=list[Asistencia], operation_id="verAsistenciaPersona"
)
def ver_asistencia_persona(
    persona_id: str, conexion: Conexion, desde: date | None = None, hasta: date | None = None
) -> list[Asistencia]:
    """RF-12 · C3: sin fechas, todas sus llegadas; con una sola, el rango queda abierto por el otro lado."""
    _exigir_rango(desde, hasta)
    persona = exigir_persona(conexion, persona_id)
    condiciones = ["a.persona_id = :persona_id"]
    if desde is not None:
        condiciones.append("a.fecha >= :desde")
    if hasta is not None:
        condiciones.append("a.fecha <= :hasta")
    filas = conexion.execute(
        text(CONSULTA + " WHERE " + " AND ".join(condiciones) + " ORDER BY a.fecha DESC"),
        {"persona_id": persona.id, "desde": desde, "hasta": hasta},
    ).all()
    return [Asistencia(**_fila(fila), fecha=fila.fecha) for fila in filas]


@router.get("/asistencia.csv", response_class=Response, operation_id="exportarAsistencia")
def exportar_asistencia(conexion: Conexion, desde: date, hasta: date) -> Response:
    """RF-06 · C4 (extra): las llegadas del rango, por fecha y hora, en CSV con coma y UTF-8."""
    _exigir_rango(desde, hasta)
    filas = conexion.execute(text(EXPORTAR), {"desde": desde, "hasta": hasta}).all()
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS_CSV)
    for fila in filas:
        escritor.writerow(
            [
                fila.fecha.isoformat(),
                _celda(fila.nombre),
                _celda(fila.documento),
                a_colombia(fila.llegada).isoformat(),
                fila.estado,
                "" if fila.minutos_tarde is None else fila.minutos_tarde,
                fila.origen,
            ]
        )
    archivo = f"asistencia-{desde.isoformat()}-a-{hasta.isoformat()}.csv"
    return Response(
        salida.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{archivo}"'},
    )
