"""
Nombre: reconocimiento.py
Descripción: Reconocer una cara (RF-04 · C2 y C3): la búsqueda central con pgvector y las reglas R1 a R4, más R7 al reconocer. Guarda el evento de acceso (RF-05 · C1 y C2) y, si es la primera entrada permitida del día, la llegada (R5, RF-06 · C1).
Fecha de creación: 2026-11-12
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 1.2
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Connection, text

from accesia import mensajes
from accesia.asistencia import Llegada, registrar_llegada
from accesia.config import configuracion
from accesia.esquemas import PersonaCorta, RespuestaRostro
from accesia.vision import FACTOR_TAMANO, Cara, Huella, cara_mas_grande, caras_validas, es_pequena

# R1: pgvector calcula la distancia en float32, así que una similitud de 0,363 puede salir 0,36299998.
# La comparación con el umbral tolera esa diferencia (specs/reglas.md, R1).
TOLERANCIA = 1e-6

BUSQUEDA = """
SELECT r.persona_id, 1 - (r.huella <=> CAST(:v AS vector)) AS similitud
FROM rostro r{filtro}
ORDER BY r.huella <=> CAST(:v AS vector)
LIMIT 1
"""


@dataclass(frozen=True)
class Parecida:
    persona_id: UUID
    similitud: float


def coincide(similitud: float, umbral: float) -> bool:
    """R1: hay coincidencia si la similitud es mayor o igual que el umbral (con la tolerancia de float32)."""
    return similitud >= umbral - TOLERANCIA


def texto_de_vector(vector: Sequence[float]) -> str:
    """La huella como texto de pgvector ([0.1,0.2,…]), con los 9 dígitos que necesita un float32."""
    return "[" + ",".join(format(float(valor), ".9g") for valor in vector) + "]"


def mas_parecida(conexion: Connection, vector: Sequence[float], excluir: UUID | None = None) -> Parecida | None:
    """La búsqueda central de modelo-datos.md: la muestra más parecida de todas (R2), o None si no hay muestras.

    Con excluir, busca solo entre las muestras de otras personas (R7, paso 5).
    """
    filtro = "" if excluir is None else " WHERE r.persona_id <> :excluir"
    fila = conexion.execute(
        text(BUSQUEDA.format(filtro=filtro)), {"v": texto_de_vector(vector), "excluir": excluir}
    ).one_or_none()
    return None if fila is None else Parecida(persona_id=fila.persona_id, similitud=float(fila.similitud))


def estado_de(activa: bool, con_consentimiento: bool) -> tuple[str, str | None]:
    """R3: inactiva gana a sin_consentimiento; solo es permitido si está activa y con consentimiento vigente."""
    if not activa:
        return "denegado", "inactiva"
    if not con_consentimiento:
        return "denegado", "sin_consentimiento"
    return "permitido", None


def guardar_evento(
    conexion: Connection,
    momento: datetime,
    dispositivo: str,
    persona_id: UUID | None,
    resultado: str,
    motivo: str | None,
    similitud: float | None,
) -> UUID:
    """Guarda el intento con la hora de accesia.tiempo.ahora(), no con now() de la base."""
    return conexion.execute(
        text(
            "INSERT INTO evento_acceso (fecha_hora, dispositivo_codigo, persona_id, resultado, motivo, similitud) "
            "VALUES (:fecha_hora, :dispositivo, :persona_id, :resultado, :motivo, :similitud) RETURNING id"
        ),
        {
            "fecha_hora": momento,
            "dispositivo": dispositivo,
            "persona_id": persona_id,
            "resultado": resultado,
            "motivo": motivo,
            "similitud": similitud,
        },
    ).scalar_one()


def evento_reciente(conexion: Connection, persona_id: UUID, dispositivo: str, resultado: str, desde: datetime):
    """R4: el último evento de la persona en esa cámara y con ese resultado guardado después de «desde»."""
    return conexion.execute(
        text(
            "SELECT id, motivo FROM evento_acceso "
            "WHERE persona_id = :persona_id AND dispositivo_codigo = :dispositivo AND resultado = :resultado "
            "AND fecha_hora > :desde ORDER BY fecha_hora DESC, id DESC LIMIT 1"
        ),
        {"persona_id": persona_id, "dispositivo": dispositivo, "resultado": resultado, "desde": desde},
    ).one_or_none()


def _respuesta(
    momento: datetime,
    resultado: str,
    motivo: str | None,
    persona: PersonaCorta | None = None,
    similitud: float | None = None,
    repetido: bool = False,
    evento_id: UUID | None = None,
) -> RespuestaRostro:
    return RespuestaRostro(
        modo="reconocer",
        resultado=resultado,
        motivo=motivo,
        persona=persona,
        similitud=similitud,
        repetido=repetido,
        evento_id=evento_id,
        inscripcion=None,
        mensaje=mensajes.de_acceso(resultado, motivo, persona.nombre if persona else None),
        hora=momento,
    )


def reconocer(
    conexion: Connection,
    dispositivo: str,
    caras: Sequence[Cara],
    huella_de: Callable[[Cara], Huella],
    momento: datetime,
    factor_tamano: float = FACTOR_TAMANO,
) -> tuple[RespuestaRostro, float | None, Llegada | None]:
    """Reconoce la cara más grande del recorte. factor_tamano es el de R7 para cara_pequena: 0,8 con un recorte y 1
    con el cuadro completo (api-dispositivo.md 1.3).

    Devuelve la respuesta, la nitidez de la cara (o None) y la llegada si este evento la creó (o None), para que B2
    la publique en el campo asistencia del Evento (mqtt.md).
    """
    conf = configuracion()
    cara = cara_mas_grande(caras_validas(caras))
    if cara is None:
        return _respuesta(momento, "descartado", "sin_cara"), None, None
    if es_pequena(cara, conf.cara_min_px, factor_tamano):
        return _respuesta(momento, "descartado", "cara_pequena"), None, None

    huella = huella_de(cara)
    parecida = mas_parecida(conexion, huella.vector)
    persona = None
    if parecida is not None and coincide(parecida.similitud, conf.umbral_similitud):
        persona = conexion.execute(
            text(
                "SELECT p.id, p.nombre, p.activa, EXISTS (SELECT 1 FROM consentimiento c "
                "WHERE c.persona_id = p.id AND c.revocado_en IS NULL) AS con_consentimiento "
                "FROM persona p WHERE p.id = :id"
            ),
            {"id": parecida.persona_id},
        ).one_or_none()

    similitud = None if parecida is None else parecida.similitud
    if persona is None:
        # R1: sin muestras o bajo el umbral. Ni la respuesta ni el evento dicen a quién se parece (RNF-01 · C3).
        evento_id = guardar_evento(conexion, momento, dispositivo, None, "desconocido", "bajo_umbral", similitud)
        respuesta = _respuesta(momento, "desconocido", "bajo_umbral", similitud=similitud, evento_id=evento_id)
        return respuesta, huella.nitidez, None

    resultado, motivo = estado_de(persona.activa, persona.con_consentimiento)
    corta = PersonaCorta(id=persona.id, nombre=persona.nombre)
    desde = momento - timedelta(seconds=conf.ventana_repetido_s)
    anterior = evento_reciente(conexion, persona.id, dispositivo, resultado, desde)
    if anterior is not None:
        # R4: no guarda nada ni cambia la asistencia, y responde con el evento original; la similitud es la de este
        # recorte.
        repetida = _respuesta(momento, resultado, anterior.motivo, corta, similitud, True, anterior.id)
        return repetida, huella.nitidez, None
    evento_id = guardar_evento(conexion, momento, dispositivo, persona.id, resultado, motivo, similitud)
    llegada = None
    if resultado == "permitido":
        # R5: la primera entrada permitida del día es la llegada, en la misma transacción del evento.
        llegada = registrar_llegada(conexion, persona.id, momento, "camara", evento_id=evento_id)
    return _respuesta(momento, resultado, motivo, corta, similitud, False, evento_id), huella.nitidez, llegada
