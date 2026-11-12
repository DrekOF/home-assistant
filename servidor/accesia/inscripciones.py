"""
Nombre: inscripciones.py
Descripción: Inscripciones (R9, RF-03): vencer, abrir, ver, cancelar y la cancelación al revocar; y cada muestra que llega de la cámara, revisada con los seis pasos de R7.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import Connection, Row, text
from sqlalchemy.exc import IntegrityError

from accesia import mensajes, tiempo
from accesia.config import configuracion
from accesia.db import VIOLACION_UNICA, violacion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Inscripcion, InscripcionCorta, InscripcionNueva, PersonaCorta, RespuestaRostro
from accesia.reconocimiento import coincide, mas_parecida, texto_de_vector
from accesia.vision import Cara, Huella, caras_validas, es_pequena

CONSULTA = """
SELECT i.id, i.persona_id, p.nombre AS persona_nombre, i.dispositivo_codigo, i.estado, i.muestras, i.requeridas,
       i.ultimo_motivo, i.creada, i.vence, i.terminada
FROM inscripcion i
JOIN persona p ON p.id = i.persona_id
"""


def vencer_inscripciones(conexion: Connection, ahora: datetime, dispositivo: str | None = None) -> int:
    """R9: las inscripciones activas cuya hora ya pasó quedan vencidas, con terminada igual a la hora en que vencieron.

    Se llama al listar o ver cámaras, al abrir, ver o cancelar una inscripción y al llegar una cara. Sin dispositivo,
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


# --- La inscripción por la API (abrirInscripcion, verInscripcion y cancelarInscripcion) ---


def _a_inscripcion(fila: Row) -> Inscripcion:
    return Inscripcion(
        id=fila.id,
        persona=PersonaCorta(id=fila.persona_id, nombre=fila.persona_nombre),
        dispositivo=fila.dispositivo_codigo,
        estado=fila.estado,
        muestras=fila.muestras,
        requeridas=fila.requeridas,
        ultimo_motivo=fila.ultimo_motivo,
        creada=fila.creada,
        vence=fila.vence,
        terminada=fila.terminada,
    )


def _al_dia(conexion: Connection, inscripcion_id: UUID, momento: datetime, bloquear: bool = False) -> Row | None:
    """La inscripción, después de vencerla si ya pasó su hora (R9); None si no existe."""
    bloqueo = " FOR UPDATE" if bloquear else ""
    fila = conexion.execute(
        text("SELECT dispositivo_codigo, estado, vence FROM inscripcion WHERE id = :id" + bloqueo),
        {"id": inscripcion_id},
    ).one_or_none()
    if fila is None:
        return None
    if fila.estado == "activa" and fila.vence <= momento:
        vencer_inscripciones(conexion, momento, fila.dispositivo_codigo)
    return conexion.execute(text(CONSULTA + " WHERE i.id = :id"), {"id": inscripcion_id}).one()


def abrir(conexion: Connection, datos: InscripcionNueva) -> Inscripcion:
    """RF-03 · C1 y R9: una inscripción para una persona con consentimiento vigente en una cámara activa."""
    momento = tiempo.ahora()
    persona = conexion.execute(
        text(
            "SELECT p.id, EXISTS (SELECT 1 FROM consentimiento c WHERE c.persona_id = p.id AND c.revocado_en IS NULL) "
            "AS con_consentimiento FROM persona p WHERE p.id = :id"
        ),
        {"id": datos.persona_id},
    ).one_or_none()
    if persona is None:
        raise ErrorAccesIA(404, "no_encontrado", "Esa persona no existe o ya fue borrada.")
    camara = conexion.execute(
        text("SELECT codigo, activo FROM dispositivo WHERE codigo = :codigo"), {"codigo": datos.dispositivo}
    ).one_or_none()
    if camara is None:
        raise ErrorAccesIA(404, "no_encontrado", f"No hay una cámara con el código {datos.dispositivo}.")
    if not camara.activo:
        # R9 pide una cámara activa y el contrato no tiene un código para esto: 422 validacion (decisión de B2).
        raise ErrorAccesIA(422, "validacion", "La cámara está desactivada: actívala antes de inscribir.")
    if not persona.con_consentimiento:
        raise ErrorAccesIA(
            422, "sin_consentimiento", "La persona no tiene un consentimiento vigente: regístralo antes de inscribirla."
        )
    vencer_inscripciones(conexion, momento, camara.codigo)
    conf = configuracion()
    try:
        with conexion.begin_nested():
            inscripcion_id = conexion.execute(
                text(
                    "INSERT INTO inscripcion (persona_id, dispositivo_codigo, requeridas, creada, vence) "
                    "VALUES (:persona_id, :dispositivo, :requeridas, :creada, :vence) RETURNING id"
                ),
                {
                    "persona_id": persona.id,
                    "dispositivo": camara.codigo,
                    "requeridas": conf.inscripcion_muestras,
                    "creada": momento,
                    "vence": momento + timedelta(seconds=conf.inscripcion_vence_s),
                },
            ).scalar_one()
    except IntegrityError as error:
        # El índice inscripcion_activa_por_camara deja una sola activa por cámara (RF-03 · C5).
        if violacion(error) == VIOLACION_UNICA:
            raise ErrorAccesIA(
                409, "inscripcion_activa", f"Ya hay una inscripción activa en la cámara {camara.codigo}."
            ) from None
        raise
    return _a_inscripcion(conexion.execute(text(CONSULTA + " WHERE i.id = :id"), {"id": inscripcion_id}).one())


def ver(conexion: Connection, inscripcion_id: UUID) -> Inscripcion | None:
    """El avance de la inscripción; si ya pasó su hora, queda vencida (R9). None si no existe."""
    fila = _al_dia(conexion, inscripcion_id, tiempo.ahora())
    return None if fila is None else _a_inscripcion(fila)


def cancelar(conexion: Connection, inscripcion_id: UUID) -> Literal["cancelada", "no_existe", "terminada"]:
    """Cancela la inscripción activa; las muestras aceptadas se conservan. Si ya pasó su hora, primero la vence."""
    momento = tiempo.ahora()
    fila = _al_dia(conexion, inscripcion_id, momento, bloquear=True)
    if fila is None:
        return "no_existe"
    if fila.estado != "activa":
        return "terminada"
    conexion.execute(
        text("UPDATE inscripcion SET estado = 'cancelada', terminada = :ahora WHERE id = :id"),
        {"ahora": momento, "id": inscripcion_id},
    )
    return "cancelada"


# --- Las muestras que llegan de la cámara (R7) ---


def activa_de(conexion: Connection, dispositivo: str) -> Row | None:
    """La inscripción activa de la cámara, bloqueada hasta el final de la transacción para contar bien las muestras."""
    return conexion.execute(
        text(
            "SELECT i.id, i.persona_id, p.nombre AS persona_nombre, i.muestras, i.requeridas, i.vence "
            "FROM inscripcion i JOIN persona p ON p.id = i.persona_id "
            "WHERE i.dispositivo_codigo = :dispositivo AND i.estado = 'activa' FOR UPDATE OF i"
        ),
        {"dispositivo": dispositivo},
    ).one_or_none()


def _similitud_con_la_primera(conexion: Connection, inscripcion_id: UUID, vector: Sequence[float]) -> float | None:
    """R7, paso 6: similitud con la primera muestra aceptada de esta inscripción; None si todavía no hay ninguna."""
    similitud = conexion.execute(
        text(
            "SELECT 1 - (r.huella <=> CAST(:v AS vector)) FROM rostro r WHERE r.inscripcion_id = :id "
            "ORDER BY r.creado, r.id LIMIT 1"
        ),
        {"v": texto_de_vector(vector), "id": inscripcion_id},
    ).scalar_one_or_none()
    return None if similitud is None else float(similitud)


def _motivo_de_rechazo(
    conexion: Connection, inscripcion: Row, caras: Sequence[Cara], huella_de: Callable[[Cara], Huella]
) -> tuple[str | None, Huella | None]:
    """Los seis pasos de R7, en orden: el primer motivo que falla, o None si la muestra sirve."""
    conf = configuracion()
    validas = caras_validas(caras)
    if not validas:
        return "sin_cara", None
    if len(validas) > 1:
        return "varias_caras", None
    if es_pequena(validas[0], conf.cara_min_px):
        return "cara_pequena", None
    huella = huella_de(validas[0])
    if huella.nitidez < conf.nitidez_min:
        return "borrosa", huella
    otra = mas_parecida(conexion, huella.vector, excluir=inscripcion.persona_id)
    if otra is not None and coincide(otra.similitud, conf.umbral_similitud):
        return "parece_otra_persona", huella
    primera = _similitud_con_la_primera(conexion, inscripcion.id, huella.vector)
    if primera is not None and not coincide(primera, conf.umbral_similitud):
        return "distinta_de_la_primera", huella
    return None, huella


def procesar_muestra(
    conexion: Connection,
    inscripcion: Row,
    fuente: str,
    caras: Sequence[Cara],
    huella_de: Callable[[Cara], Huella],
    momento: datetime,
) -> tuple[RespuestaRostro, float | None]:
    """RF-03 · C2 y C3: guarda la muestra si pasa R7 y suma una; al llegar a las requeridas, la inscripción se completa.

    Devuelve la respuesta (persona es siempre quien se inscribe) y la nitidez de la cara, si se midió.
    """
    motivo, huella = _motivo_de_rechazo(conexion, inscripcion, caras, huella_de)
    if motivo is not None:
        fila = conexion.execute(
            text(
                "UPDATE inscripcion SET ultimo_motivo = :motivo WHERE id = :id "
                "RETURNING muestras, requeridas, estado, vence"
            ),
            {"motivo": motivo, "id": inscripcion.id},
        ).one()
    else:
        assert huella is not None
        conexion.execute(
            text(
                "INSERT INTO rostro (persona_id, inscripcion_id, huella, fuente, calidad, creado) "
                "VALUES (:persona_id, :inscripcion_id, CAST(:huella AS vector), :fuente, :calidad, :creado)"
            ),
            {
                "persona_id": inscripcion.persona_id,
                "inscripcion_id": inscripcion.id,
                "huella": texto_de_vector(huella.vector),
                "fuente": fuente,
                "calidad": huella.nitidez,
                "creado": momento,
            },
        )
        # En el UPDATE, «muestras» es el valor de antes: con la última requerida, la inscripción queda completada.
        fila = conexion.execute(
            text(
                "UPDATE inscripcion SET muestras = muestras + 1, "
                "estado = CASE WHEN muestras + 1 >= requeridas THEN 'completada' ELSE estado END, "
                "terminada = CASE WHEN muestras + 1 >= requeridas THEN :ahora ELSE terminada END "
                "WHERE id = :id RETURNING muestras, requeridas, estado, vence"
            ),
            {"ahora": momento, "id": inscripcion.id},
        ).one()
    respuesta = RespuestaRostro(
        modo="inscribir",
        resultado="muestra_rechazada" if motivo else "muestra_aceptada",
        motivo=motivo,
        persona=PersonaCorta(id=inscripcion.persona_id, nombre=inscripcion.persona_nombre),
        similitud=None,
        repetido=False,
        evento_id=None,
        inscripcion=InscripcionCorta(
            id=inscripcion.id, muestras=fila.muestras, requeridas=fila.requeridas, estado=fila.estado, vence=fila.vence
        ),
        mensaje=mensajes.de_muestra(motivo, fila.muestras, fila.requeridas),
        hora=momento,
    )
    return respuesta, None if huella is None else huella.nitidez
