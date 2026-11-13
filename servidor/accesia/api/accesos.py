"""
Nombre: accesos.py
Descripción: Ruta listarAccesos: los eventos de acceso con filtros por fechas, resultado, persona y cámara, con paginación, del más reciente al más antiguo (RF-05 · C3).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime
from sqlalchemy import text

from accesia.db import Conexion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import EventoAcceso, PaginaEventos, PersonaCorta, ResultadoAcceso
from accesia.sesion import administrador_actual

router = APIRouter(prefix="/api/v1", tags=["Accesos"], dependencies=[Depends(administrador_actual)])

CONSULTA = """
SELECT e.id, e.fecha_hora, e.dispositivo_codigo, e.resultado, e.motivo, e.similitud,
       p.id AS persona_id, p.nombre AS persona_nombre
FROM evento_acceso e
LEFT JOIN persona p ON p.id = e.persona_id
"""

# Del más reciente al más antiguo; con la misma hora, el último guardado primero (los id son uuidv7).
ORDEN = " ORDER BY e.fecha_hora DESC, e.id DESC"


@router.get("/accesos", response_model=PaginaEventos, operation_id="listarAccesos")
def listar_accesos(
    conexion: Conexion,
    desde: AwareDatetime | None = None,
    hasta: AwareDatetime | None = None,
    resultado: ResultadoAcceso | None = None,
    persona_id: UUID | None = None,
    dispositivo: Annotated[str | None, Query(pattern=r"^[a-z0-9-]{3,32}$")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaEventos:
    """desde y hasta (con zona) entran en el rango. Una persona o una cámara que no existe da una página vacía."""
    if desde is not None and hasta is not None and desde > hasta:
        raise ErrorAccesIA(422, "validacion", "La fecha «desde» no puede ser posterior a «hasta».")
    filtros = {
        "e.fecha_hora >= :desde": desde,
        "e.fecha_hora <= :hasta": hasta,
        "e.resultado = :resultado": resultado,
        "e.persona_id = :persona_id": persona_id,
        "e.dispositivo_codigo = :dispositivo": dispositivo,
    }
    condiciones = [condicion for condicion, valor in filtros.items() if valor is not None]
    donde = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    valores = {
        "desde": desde,
        "hasta": hasta,
        "resultado": resultado,
        "persona_id": persona_id,
        "dispositivo": dispositivo,
    }
    total = conexion.execute(text("SELECT count(*) FROM evento_acceso e" + donde), valores).scalar_one()
    filas = conexion.execute(
        text(CONSULTA + donde + ORDEN + " LIMIT :limite OFFSET :salto"),
        {**valores, "limite": por_pagina, "salto": (pagina - 1) * por_pagina},
    ).all()
    elementos = [
        EventoAcceso(
            id=fila.id,
            fecha_hora=fila.fecha_hora,
            dispositivo=fila.dispositivo_codigo,
            resultado=fila.resultado,
            motivo=fila.motivo,
            persona=None if fila.persona_id is None else PersonaCorta(id=fila.persona_id, nombre=fila.persona_nombre),
            similitud=fila.similitud,
        )
        for fila in filas
    ]
    return PaginaEventos(elementos=elementos, total=total, pagina=pagina, por_pagina=por_pagina)
