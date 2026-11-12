"""
Nombre: consentimiento.py
Descripción: Rutas del consentimiento: texto vigente, ver, registrar, revocar e historial (RF-02 · C2, C3 y C5; Ley 1581).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from accesia.api.personas import exigir_persona, id_de_persona
from accesia.config import configuracion
from accesia.consentimiento import texto_vigente
from accesia.db import VIOLACION_UNICA, Conexion, violacion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Consentimiento, ConsentimientoNuevo, TextoConsentimiento
from accesia.inscripciones import cancelar_inscripcion_de
from accesia.sesion import AdministradorDeLaSesion, administrador_actual
from accesia.tiempo import ahora

router = APIRouter(prefix="/api/v1", tags=["Consentimiento"], dependencies=[Depends(administrador_actual)])

CONSULTA = """
SELECT c.id, c.persona_id, c.version_texto, c.medio, a.nombre AS registrado_por, c.aceptado_en, c.revocado_en
FROM consentimiento c
LEFT JOIN administrador a ON a.id = c.registrado_por
"""


def _vigente(conexion: Connection, persona_id: UUID) -> Consentimiento | None:
    fila = conexion.execute(
        text(CONSULTA + " WHERE c.persona_id = :persona_id AND c.revocado_en IS NULL"), {"persona_id": persona_id}
    ).one_or_none()
    return None if fila is None else Consentimiento(**fila._mapping)


def _ya_tiene_uno() -> ErrorAccesIA:
    return ErrorAccesIA(409, "consentimiento_vigente", "Esta persona ya tiene un consentimiento vigente.")


@router.get("/consentimiento/texto", response_model=TextoConsentimiento, operation_id="verTextoConsentimiento")
def ver_texto() -> TextoConsentimiento:
    return texto_vigente()


@router.get(
    "/personas/{persona_id}/consentimiento", response_model=Consentimiento | None, operation_id="verConsentimiento"
)
def ver_consentimiento(persona_id: str, conexion: Conexion) -> Consentimiento | None:
    # null si no hay uno vigente; 404 solo si la persona no existe.
    persona = exigir_persona(conexion, persona_id)
    return _vigente(conexion, persona.id)


@router.post(
    "/personas/{persona_id}/consentimiento",
    status_code=201,
    response_model=Consentimiento,
    operation_id="registrarConsentimiento",
)
def registrar_consentimiento(
    persona_id: str, datos: ConsentimientoNuevo, administrador: AdministradorDeLaSesion, conexion: Conexion
) -> Consentimiento:
    persona = exigir_persona(conexion, persona_id)
    vigente = texto_vigente().version
    if datos.version_texto != vigente:
        raise ErrorAccesIA(
            422,
            "version_texto_invalida",
            f"El texto vigente es la versión {vigente}. Recarga la ficha y muéstrale a la persona el texto actual.",
        )
    if _vigente(conexion, persona.id) is not None:
        raise _ya_tiene_uno()
    momento = ahora()
    aceptado_en = momento
    # Con papel, aceptado_en es la hora de la firma; con web, o si falta, la hora del registro.
    if datos.medio == "papel" and datos.aceptado_en is not None:
        if datos.aceptado_en > datetime.now(configuracion().zona):
            raise ErrorAccesIA(422, "validacion", "La fecha de la firma no puede ser futura.")
        aceptado_en = datos.aceptado_en.replace(microsecond=0)
    try:
        with conexion.begin_nested():
            consentimiento_id = conexion.execute(
                text(
                    "INSERT INTO consentimiento (persona_id, version_texto, medio, registrado_por, aceptado_en) "
                    "VALUES (:persona_id, :version_texto, :medio, :registrado_por, :aceptado_en) RETURNING id"
                ),
                {
                    "persona_id": persona.id,
                    "version_texto": vigente,
                    "medio": datos.medio,
                    "registrado_por": administrador.id,
                    "aceptado_en": aceptado_en,
                },
            ).scalar_one()
    except IntegrityError as error:
        # Dos registros a la vez: el índice consentimiento_vigente_unico deja pasar solo uno.
        if violacion(error) == VIOLACION_UNICA:
            raise _ya_tiene_uno() from None
        raise
    conexion.execute(text("UPDATE persona SET actualizada = :ahora WHERE id = :id"), {"ahora": momento, "id": persona.id})
    fila = conexion.execute(text(CONSULTA + " WHERE c.id = :id"), {"id": consentimiento_id}).one()
    return Consentimiento(**fila._mapping)


@router.delete("/personas/{persona_id}/consentimiento", status_code=204, operation_id="revocarConsentimiento")
def revocar_consentimiento(persona_id: str, conexion: Conexion) -> None:
    """RF-02 · C5: en la misma transacción revoca, borra las huellas y cancela la inscripción activa (R9)."""
    momento = ahora()
    revocado = conexion.execute(
        text(
            "UPDATE consentimiento SET revocado_en = :ahora "
            "WHERE persona_id = :persona_id AND revocado_en IS NULL RETURNING persona_id"
        ),
        {"ahora": momento, "persona_id": id_de_persona(persona_id)},
    ).one_or_none()
    if revocado is None:
        raise ErrorAccesIA(404, "no_encontrado", "La persona no existe o no tiene un consentimiento vigente.")
    conexion.execute(text("DELETE FROM rostro WHERE persona_id = :persona_id"), {"persona_id": revocado.persona_id})
    cancelar_inscripcion_de(conexion, revocado.persona_id, momento)
    conexion.execute(
        text("UPDATE persona SET actualizada = :ahora WHERE id = :id"), {"ahora": momento, "id": revocado.persona_id}
    )


@router.get(
    "/personas/{persona_id}/consentimientos",
    response_model=list[Consentimiento],
    operation_id="listarConsentimientos",
)
def listar_consentimientos(persona_id: str, conexion: Conexion) -> list[Consentimiento]:
    persona = exigir_persona(conexion, persona_id)
    filas = conexion.execute(
        text(CONSULTA + " WHERE c.persona_id = :persona_id ORDER BY c.aceptado_en DESC, c.id DESC"),
        {"persona_id": persona.id},
    ).all()
    return [Consentimiento(**fila._mapping) for fila in filas]
