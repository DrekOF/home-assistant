"""
Nombre: personas.py
Descripción: Rutas de personas: listar con búsqueda y paginación, crear, ver, editar y borrar (RF-02 · C1, RF-12 · C2).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from accesia.db import VIOLACION_LLAVE_FORANEA, VIOLACION_UNICA, Conexion, violacion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import PaginaPersonas, Persona, PersonaCambios, PersonaNueva
from accesia.sesion import administrador_actual
from accesia.tiempo import ahora

router = APIRouter(prefix="/api/v1", tags=["Personas"], dependencies=[Depends(administrador_actual)])

CONSULTA = """
SELECT p.id, p.documento, p.nombre, p.rol, p.horario_id, h.nombre AS horario_nombre, p.activa,
       EXISTS (SELECT 1 FROM consentimiento c WHERE c.persona_id = p.id AND c.revocado_en IS NULL)
           AS consentimiento_vigente,
       (SELECT count(*) FROM rostro r WHERE r.persona_id = p.id) AS muestras,
       p.creada, p.actualizada
FROM persona p
LEFT JOIN horario h ON h.id = p.horario_id
"""

# Orden por nombre con la colación española, como localeCompare(…, 'es') del simulacro de la web.
ORDEN = ' ORDER BY p.nombre COLLATE "es-x-icu", p.id'

# Campos de PersonaCambios que se pueden escribir: la lista es cerrada, nunca sale de la petición.
CAMPOS_EDITABLES = ("documento", "nombre", "rol", "horario_id", "activa")


def no_existe() -> ErrorAccesIA:
    return ErrorAccesIA(404, "no_encontrado", "Esa persona no existe o ya fue borrada.")


def id_de_persona(texto: str) -> UUID | None:
    """El id de la ruta; un texto que no es un uuid es una persona que no existe (404), como en el simulacro."""
    try:
        return UUID(texto)
    except ValueError:
        return None


def buscar_persona(conexion: Connection, persona_id: UUID | None) -> Persona | None:
    if persona_id is None:
        return None
    fila = conexion.execute(text(CONSULTA + " WHERE p.id = :id"), {"id": persona_id}).one_or_none()
    return None if fila is None else Persona(**fila._mapping)


def exigir_persona(conexion: Connection, texto_id: str) -> Persona:
    """La persona de la ruta, o 404 no_encontrado."""
    persona = buscar_persona(conexion, id_de_persona(texto_id))
    if persona is None:
        raise no_existe()
    return persona


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@contextmanager
def _errores_de_persona(conexion: Connection, documento: str | None) -> Iterator[None]:
    """Traduce los errores de la base a códigos del contrato. El savepoint deja la transacción sana tras el error."""
    try:
        with conexion.begin_nested():
            yield
    except IntegrityError as error:
        estado = violacion(error)
        if estado == VIOLACION_UNICA:
            raise ErrorAccesIA(409, "documento_duplicado", f"Ya hay una persona con el documento {documento}.") from None
        if estado == VIOLACION_LLAVE_FORANEA:
            raise ErrorAccesIA(422, "validacion", "Ese horario no existe.") from None
        raise


@router.get("/personas", response_model=PaginaPersonas, operation_id="listarPersonas")
def listar_personas(
    conexion: Conexion,
    q: Annotated[str | None, Query(max_length=60)] = None,
    activa: bool | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaPersonas:
    condiciones: list[str] = []
    valores: dict[str, object] = {}
    if q and q.strip():
        # Sin importar tildes ni mayúsculas; % y _ de la búsqueda valen como letras, no como comodines.
        condiciones.append(
            "(lower(unaccent(p.nombre)) LIKE '%' || lower(unaccent(:q)) || '%' ESCAPE '\\'"
            " OR lower(unaccent(p.documento)) LIKE '%' || lower(unaccent(:q)) || '%' ESCAPE '\\')"
        )
        valores["q"] = _escapar_like(q.strip())
    if activa is not None:
        condiciones.append("p.activa = :activa")
        valores["activa"] = activa
    donde = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    total = conexion.execute(text("SELECT count(*) FROM persona p" + donde), valores).scalar_one()
    filas = conexion.execute(
        text(CONSULTA + donde + ORDEN + " LIMIT :limite OFFSET :desde"),
        {**valores, "limite": por_pagina, "desde": (pagina - 1) * por_pagina},
    ).all()
    return PaginaPersonas(
        elementos=[Persona(**fila._mapping) for fila in filas], total=total, pagina=pagina, por_pagina=por_pagina
    )


@router.post("/personas", status_code=201, response_model=Persona, operation_id="crearPersona")
def crear_persona(datos: PersonaNueva, conexion: Conexion) -> Persona:
    with _errores_de_persona(conexion, datos.documento):
        persona_id = conexion.execute(
            text(
                "INSERT INTO persona (documento, nombre, rol, horario_id, activa) "
                "VALUES (:documento, :nombre, :rol, :horario_id, :activa) RETURNING id"
            ),
            datos.model_dump(),
        ).scalar_one()
    persona = buscar_persona(conexion, persona_id)
    assert persona is not None
    return persona


@router.get("/personas/{persona_id}", response_model=Persona, operation_id="verPersona")
def ver_persona(persona_id: str, conexion: Conexion) -> Persona:
    return exigir_persona(conexion, persona_id)


@router.patch("/personas/{persona_id}", response_model=Persona, operation_id="editarPersona")
def editar_persona(persona_id: str, cambios: PersonaCambios, conexion: Conexion) -> Persona:
    persona = exigir_persona(conexion, persona_id)
    valores = {campo: valor for campo, valor in cambios.valores().items() if campo in CAMPOS_EDITABLES}
    asignaciones = ", ".join(f"{campo} = :{campo}" for campo in valores)
    with _errores_de_persona(conexion, valores.get("documento")):
        conexion.execute(
            text(f"UPDATE persona SET {asignaciones}, actualizada = :ahora WHERE id = :id"),
            {**valores, "ahora": ahora(), "id": persona.id},
        )
    actualizada = buscar_persona(conexion, persona.id)
    assert actualizada is not None
    return actualizada


@router.delete("/personas/{persona_id}", status_code=204, operation_id="borrarPersona")
def borrar_persona(persona_id: str, conexion: Conexion) -> None:
    # La base borra sus huellas, consentimientos, inscripciones y asistencia, y deja sus eventos sin persona (RF-12 · C2).
    borrada = conexion.execute(
        text("DELETE FROM persona WHERE id = :id RETURNING id"), {"id": id_de_persona(persona_id)}
    ).one_or_none()
    if borrada is None:
        raise no_existe()
