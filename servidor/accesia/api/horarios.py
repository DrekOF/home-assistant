"""
Nombre: horarios.py
Descripción: Rutas de horarios por bloques: listar, crear, editar y borrar (RF-13 · C1 a C3, D-20).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from accesia.db import VIOLACION_RESTRICT, VIOLACION_UNICA, Conexion, violacion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Horario, HorarioBloque, HorarioCambios, HorarioNuevo
from accesia.sesion import administrador_actual

router = APIRouter(prefix="/api/v1", tags=["Horarios"], dependencies=[Depends(administrador_actual)])

CONSULTA = """
SELECT h.id, h.nombre,
       coalesce(
           json_agg(
               json_build_object('dia', b.dia, 'hora_inicio', to_char(b.hora_inicio, 'HH24:MI'),
                                 'tolerancia_min', b.tolerancia_min)
               ORDER BY b.dia
           ) FILTER (WHERE b.horario_id IS NOT NULL),
           '[]'::json
       ) AS bloques
FROM horario h
LEFT JOIN horario_bloque b ON b.horario_id = h.id
"""
AGRUPAR = " GROUP BY h.id, h.nombre"


def _no_existe() -> ErrorAccesIA:
    return ErrorAccesIA(404, "no_encontrado", "Ese horario no existe o ya fue borrado.")


def _id_de_horario(texto: str) -> UUID | None:
    try:
        return UUID(texto)
    except ValueError:
        return None


def _buscar(conexion: Connection, horario_id: UUID | None) -> Horario | None:
    if horario_id is None:
        return None
    fila = conexion.execute(text(CONSULTA + " WHERE h.id = :id" + AGRUPAR), {"id": horario_id}).one_or_none()
    return None if fila is None else Horario(**fila._mapping)


@contextmanager
def _nombre_libre(conexion: Connection, nombre: str | None) -> Iterator[None]:
    """Un nombre repetido es 409 nombre_duplicado. El savepoint deja la transacción sana tras el error."""
    try:
        with conexion.begin_nested():
            yield
    except IntegrityError as error:
        if violacion(error) == VIOLACION_UNICA:
            raise ErrorAccesIA(409, "nombre_duplicado", f"Ya hay un horario con el nombre «{nombre}».") from None
        raise


def _guardar_bloques(conexion: Connection, horario_id: UUID, bloques: list[HorarioBloque]) -> None:
    """Reemplaza la lista completa de bloques del horario (RF-13 · C2)."""
    conexion.execute(text("DELETE FROM horario_bloque WHERE horario_id = :id"), {"id": horario_id})
    conexion.execute(
        text(
            "INSERT INTO horario_bloque (horario_id, dia, hora_inicio, tolerancia_min) "
            "VALUES (:horario_id, :dia, CAST(:hora_inicio AS time), :tolerancia_min)"
        ),
        [{"horario_id": horario_id, **bloque.model_dump()} for bloque in bloques],
    )


@router.get("/horarios", response_model=list[Horario], operation_id="listarHorarios")
def listar_horarios(conexion: Conexion) -> list[Horario]:
    filas = conexion.execute(text(CONSULTA + AGRUPAR + ' ORDER BY h.nombre COLLATE "es-x-icu", h.id')).all()
    return [Horario(**fila._mapping) for fila in filas]


@router.post("/horarios", status_code=201, response_model=Horario, operation_id="crearHorario")
def crear_horario(datos: HorarioNuevo, conexion: Conexion) -> Horario:
    with _nombre_libre(conexion, datos.nombre):
        horario_id = conexion.execute(
            text("INSERT INTO horario (nombre) VALUES (:nombre) RETURNING id"), {"nombre": datos.nombre}
        ).scalar_one()
    _guardar_bloques(conexion, horario_id, datos.bloques)
    horario = _buscar(conexion, horario_id)
    assert horario is not None
    return horario


@router.patch("/horarios/{horario_id}", response_model=Horario, operation_id="editarHorario")
def editar_horario(horario_id: str, cambios: HorarioCambios, conexion: Conexion) -> Horario:
    horario = _buscar(conexion, _id_de_horario(horario_id))
    if horario is None:
        raise _no_existe()
    if cambios.nombre is not None:
        with _nombre_libre(conexion, cambios.nombre):
            conexion.execute(
                text("UPDATE horario SET nombre = :nombre WHERE id = :id"), {"nombre": cambios.nombre, "id": horario.id}
            )
    if cambios.bloques is not None:
        _guardar_bloques(conexion, horario.id, cambios.bloques)
    actualizado = _buscar(conexion, horario.id)
    assert actualizado is not None
    return actualizado


@router.delete("/horarios/{horario_id}", status_code=204, operation_id="borrarHorario")
def borrar_horario(horario_id: str, conexion: Conexion) -> None:
    try:
        with conexion.begin_nested():
            borrado = conexion.execute(
                text("DELETE FROM horario WHERE id = :id RETURNING id"), {"id": _id_de_horario(horario_id)}
            ).one_or_none()
    except IntegrityError as error:
        # persona.horario_id es ON DELETE RESTRICT: PostgreSQL responde restrict_violation (23001).
        if violacion(error) == VIOLACION_RESTRICT:
            raise ErrorAccesIA(
                409, "horario_en_uso", "No se puede borrar: hay personas con este horario. Cámbiales el horario primero."
            ) from None
        raise
    if borrado is None:
        raise _no_existe()
