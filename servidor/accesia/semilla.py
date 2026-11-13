"""
Nombre: semilla.py
Descripción: Semilla del agente (contratos/mcp-agente.md, Evaluación): crea las seis personas, el horario, los consentimientos y los eventos de la evaluación con fechas relativas a hoy, reemplaza o borra solo lo suyo y revisa las preguntas 1 a 9 con las herramientas.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Convive con datos reales, por ejemplo los del Hito 1:
- si la base tiene personas o eventos que no son suyos, no escribe nada, salvo que se pida con_datos_reales;
- nunca cambia ni borra lo que no creó. Reconoce lo suyo por identificadores fijos (uuid5 de un espacio propio):
  sus personas (documentos SEMILLA-01 a SEMILLA-06), su horario y sus eventos.

Las llegadas se califican con R5, con registrar_llegada de accesia.asistencia (B1 del Día 3).
"""

import unicodedata
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import Connection, text

from accesia import agente, camaras, tiempo
from accesia.asistencia import registrar_llegada
from accesia.consentimiento import texto_vigente
from accesia.esquemas import DispositivoNuevo

# Todos los identificadores de la semilla salen de este espacio: así sabe qué filas son suyas.
ESPACIO = uuid.UUID("3f6b2c1e-8d4a-4b7e-9a51-5e17a5ed0b03")

HORARIO = "Clase todos los días"
HORARIO_ID = uuid.uuid5(ESPACIO, "horario")
HORA_DE_CLASE = time(7, 0)
TOLERANCIA_MIN = 10
CAMARA = "entrada"


@dataclass(frozen=True)
class PersonaDeLaSemilla:
    documento: str
    nombre: str
    rol: str = "estudiante"
    con_horario: bool = True
    activa: bool = True

    @property
    def id(self) -> uuid.UUID:
        return uuid.uuid5(ESPACIO, f"persona/{self.documento}")


# La tabla de personas de la evaluación (mcp-agente.md).
PERSONAS = (
    PersonaDeLaSemilla("SEMILLA-01", "Ana Gómez"),
    PersonaDeLaSemilla("SEMILLA-02", "Bruno Díaz"),
    PersonaDeLaSemilla("SEMILLA-03", "Carla Ruiz"),
    PersonaDeLaSemilla("SEMILLA-04", "David Peña", rol="docente", con_horario=False),
    PersonaDeLaSemilla("SEMILLA-05", "Elena Mora", activa=False),
    PersonaDeLaSemilla("SEMILLA-06", "Felipe Soto"),
)
POR_DOCUMENTO = {persona.documento: persona for persona in PERSONAS}


@dataclass(frozen=True)
class EventoDeLaSemilla:
    """Un intento de acceso: a una hora de hace unos días (dias_atras y hora) o a un tiempo antes de ahora (antes)."""

    clave: str
    documento: str | None
    resultado: str = "permitido"
    motivo: str | None = None
    similitud: float = 0.71
    dias_atras: int | None = None
    hora: time | None = None
    antes: timedelta | None = None

    @property
    def id(self) -> uuid.UUID:
        return uuid.uuid5(ESPACIO, f"evento/{self.clave}")

    def momento(self, ahora: datetime) -> datetime:
        if self.antes is not None:
            return ahora - self.antes
        assert self.dias_atras is not None and self.hora is not None
        return datetime.combine(ahora.date() - timedelta(days=self.dias_atras), self.hora, tzinfo=ahora.tzinfo)


def _llegada(clave: str, documento: str, dias_atras: int, hora: str, similitud: float) -> EventoDeLaSemilla:
    horas, minutos = (int(parte) for parte in hora.split(":"))
    return EventoDeLaSemilla(clave, documento, similitud=similitud, dias_atras=dias_atras, hora=time(horas, minutos))


def _desconocido(clave: str, antes: timedelta, similitud: float) -> EventoDeLaSemilla:
    return EventoDeLaSemilla(clave, None, "desconocido", "bajo_umbral", similitud, antes=antes)


# La tabla de eventos de la evaluación (mcp-agente.md).
EVENTOS = (
    _llegada("antier-ana", "SEMILLA-01", 2, "07:20", 0.71),
    _llegada("antier-bruno", "SEMILLA-02", 2, "06:50", 0.68),
    _llegada("antier-carla", "SEMILLA-03", 2, "07:00", 0.74),
    _llegada("antier-felipe", "SEMILLA-06", 2, "07:11", 0.66),
    _llegada("ayer-ana", "SEMILLA-01", 1, "06:58", 0.72),
    _llegada("ayer-bruno", "SEMILLA-02", 1, "07:05", 0.69),
    _llegada("ayer-carla", "SEMILLA-03", 1, "07:12", 0.73),
    _llegada("ayer-david", "SEMILLA-04", 1, "07:40", 0.70),
    EventoDeLaSemilla("ayer-elena", "SEMILLA-05", "denegado", "inactiva", 0.67, dias_atras=1, hora=time(7, 45)),
    _llegada("ayer-ana-otra-vez", "SEMILLA-01", 1, "09:30", 0.70),
    # Hace 2 horas, 3 desconocidos en 41 s; hace 30 horas, 1 desconocido.
    _desconocido("desconocido-1", timedelta(hours=2), 0.21),
    _desconocido("desconocido-2", timedelta(hours=2) - timedelta(seconds=20), 0.18),
    _desconocido("desconocido-3", timedelta(hours=2) - timedelta(seconds=41), 0.24),
    _desconocido("desconocido-viejo", timedelta(hours=30), 0.19),
)
EVENTO_IDS = [evento.id for evento in EVENTOS]
PERSONA_IDS = [persona.id for persona in PERSONAS]


def _contar(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


class ErrorDeSemilla(Exception):
    """La semilla no escribió nada; el texto dice por qué y qué hacer."""


@dataclass(frozen=True)
class Ajenos:
    """Lo que hay en la base y no creó la semilla."""

    personas: int
    eventos: int

    def __bool__(self) -> bool:
        return bool(self.personas or self.eventos)


@dataclass(frozen=True)
class Borrado:
    personas: int
    eventos: int
    horario: bool


# --- Revisión de las preguntas 1 a 9 con las herramientas ---


def _sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()


def _estado(estado: str) -> str:
    return {"a_tiempo": "a tiempo", "tarde": "tarde", "sin_horario": "sin horario"}[estado]


def _cuando(fecha: str) -> str:
    """«antier» o «ayer» si la fecha es una de esas; si no, la fecha."""
    dias = (agente.hoy() - date.fromisoformat(fecha)).days
    return {0: "hoy", 1: "ayer", 2: "antier"}.get(dias, fecha)


def _tardes(resultado: dict[str, Any]) -> str:
    return ", ".join(f"{llegada['nombre']}, {llegada['minutos_tarde']} minutos" for llegada in resultado["tarde"]) or "nadie"


def _llegada_de_ana(resultado: dict[str, Any]) -> str:
    llegadas = [
        f"{llegada['nombre']}: {llegada['llegada']}, {_estado(estado)}"
        for estado in ("a_tiempo", "tarde", "sin_horario")
        for llegada in resultado[estado]
        if "ana" in _sin_tildes(llegada["nombre"]).split()
    ]
    return "; ".join(llegadas) or "no llegó"


def _tardes_por_dia(resultado: dict[str, Any]) -> str:
    return ", ".join(
        f"{llegada['nombre']} ({_cuando(llegada['fecha'])}, {llegada['minutos_tarde']} min)"
        for llegada in resultado["llegadas"]
    ) or "nadie"


def _desconocidos(resultado: dict[str, Any]) -> str:
    if not resultado["total"]:
        return "No"
    camaras_ = ", ".join(f"{cantidad} en la cámara {camara}" for camara, cantidad in resultado["por_camara"].items())
    return f"Sí, {camaras_}"


def _activas(resultado: dict[str, Any]) -> str:
    personas = resultado["personas"]
    if not personas:
        return "No está registrada"
    return "; ".join(f"{persona['nombre']}: {'activa' if persona['activa'] else 'inactiva'}" for persona in personas)


def _accesos(resultado: dict[str, Any]) -> str:
    if "coincidencias" in resultado:
        return ", ".join(resultado["coincidencias"]) or resultado["mensaje"]
    horas = " y ".join(acceso["hora"] for acceso in resultado["accesos"])
    return f"{resultado['total']} veces: {horas}"


@dataclass(frozen=True)
class Pregunta:
    """Una pregunta de la evaluación con su herramienta esperada y la respuesta del contrato, en pocas palabras."""

    numero: int
    texto: str
    herramienta: str
    argumentos: dict[str, Any]
    esperado: str
    resumir: Callable[[dict[str, Any]], str]


PREGUNTAS = (
    Pregunta(1, "¿Quién llegó tarde ayer?", "asistencia_del_dia", {"fecha": "ayer"}, "Carla Ruiz, 12 minutos",
             _tardes),
    Pregunta(2, "¿Quién faltó ayer?", "asistencia_del_dia", {"fecha": "ayer"}, "Felipe Soto",
             lambda resultado: ", ".join(resultado["ausentes"]) or "nadie"),
    Pregunta(3, "¿A qué hora llegó Ana ayer?", "asistencia_del_dia", {"fecha": "ayer"}, "Ana Gómez: 06:58, a tiempo",
             _llegada_de_ana),
    Pregunta(4, "¿Cuántas personas llegaron ayer?", "asistencia_del_dia", {"fecha": "ayer"}, "4",
             lambda resultado: str(resultado["total_llegadas"])),
    Pregunta(5, "¿Quiénes llegaron tarde antier y ayer?", "llegadas_tarde", {"desde": "antier", "hasta": "ayer"},
             "Felipe Soto (antier, 11 min), Ana Gómez (antier, 20 min), Carla Ruiz (ayer, 12 min)", _tardes_por_dia),
    Pregunta(6, "¿Hubo desconocidos en las últimas 24 horas?", "desconocidos_recientes", {"horas": 24},
             "Sí, 3 en la cámara entrada", _desconocidos),
    Pregunta(7, "¿Elena Mora puede entrar?", "buscar_persona", {"nombre": "Elena Mora"}, "Elena Mora: inactiva",
             _activas),
    Pregunta(8, "¿Cuántas veces entró Ana ayer?", "accesos_de_persona", {"nombre": "Ana", "desde": "ayer",
             "hasta": "ayer"}, "2 veces: 06:58 y 09:30", _accesos),
    Pregunta(9, "¿Quién es Zoe Vargas?", "buscar_persona", {"nombre": "Zoe Vargas"}, "No está registrada", _activas),
)

CONSULTAS: dict[str, Callable[..., dict[str, Any]]] = {
    "buscar_persona": agente.buscar_persona,
    "asistencia_del_dia": agente.asistencia_del_dia,
    "llegadas_tarde": agente.llegadas_tarde,
    "accesos_de_persona": agente.accesos_de_persona,
    "desconocidos_recientes": agente.desconocidos_recientes,
}


@dataclass(frozen=True)
class Revisada:
    pregunta: Pregunta
    obtenido: str

    @property
    def coincide(self) -> bool:
        return self.obtenido == self.pregunta.esperado


def revisar(conexion: Connection) -> list[Revisada]:
    """Responde las preguntas 1 a 9 con las mismas consultas de las herramientas, con los datos que hay ahora."""
    revisadas = []
    for pregunta in PREGUNTAS:
        try:
            obtenido = pregunta.resumir(CONSULTAS[pregunta.herramienta](conexion, **pregunta.argumentos))
        except agente.ErrorDeHerramienta as error:
            obtenido = f"error: {error}"
        revisadas.append(Revisada(pregunta, obtenido))
    return revisadas


# --- Crear y borrar ---


@dataclass(frozen=True)
class Resultado:
    hoy: date
    personas: int
    eventos: int
    llegadas: int
    camara_creada: bool
    ajenos: Ajenos
    revision: list[Revisada]


def datos_ajenos(conexion: Connection) -> Ajenos:
    personas = conexion.execute(
        text("SELECT count(*) FROM persona WHERE NOT (id = ANY(:ids))"), {"ids": PERSONA_IDS}
    ).scalar_one()
    eventos = conexion.execute(
        text("SELECT count(*) FROM evento_acceso WHERE NOT (id = ANY(:ids))"), {"ids": EVENTO_IDS}
    ).scalar_one()
    return Ajenos(personas, eventos)


def _revisar_conflictos(conexion: Connection) -> None:
    """Un horario o un documento que la semilla usaría, pero que no es suyo: no lo toca y no sigue."""
    horario = conexion.execute(text("SELECT id FROM horario WHERE nombre = :nombre"), {"nombre": HORARIO}).scalar()
    if horario is not None and horario != HORARIO_ID:
        raise ErrorDeSemilla(
            f"Ya hay un horario «{HORARIO}» que no creó la semilla. Cámbiale el nombre en la web y vuelve a correrla."
        )
    ocupados = conexion.execute(
        text("SELECT documento FROM persona WHERE documento = ANY(:documentos) AND NOT (id = ANY(:ids))"),
        {"documentos": list(POR_DOCUMENTO), "ids": PERSONA_IDS},
    ).scalars().all()
    if ocupados:
        raise ErrorDeSemilla(
            f"Ya hay personas con los documentos {', '.join(ocupados)} que no creó la semilla. No las toco: cámbiales el "
            "documento en la web y vuelve a correrla."
        )


def borrar(conexion: Connection) -> Borrado:
    """Borra solo lo que creó la semilla: sus eventos, sus personas (con sus consentimientos y llegadas) y su horario,
    si nadie más lo usa. La cámara no se borra."""
    eventos = conexion.execute(text("DELETE FROM evento_acceso WHERE id = ANY(:ids)"), {"ids": EVENTO_IDS}).rowcount
    personas = conexion.execute(text("DELETE FROM persona WHERE id = ANY(:ids)"), {"ids": PERSONA_IDS}).rowcount
    en_uso = conexion.execute(
        text("SELECT EXISTS (SELECT 1 FROM persona WHERE horario_id = :horario)"), {"horario": HORARIO_ID}
    ).scalar_one()
    horario = False
    if not en_uso:
        horario = conexion.execute(text("DELETE FROM horario WHERE id = :horario"), {"horario": HORARIO_ID}).rowcount > 0
    return Borrado(personas=personas, eventos=eventos, horario=horario)


def _crear_horario(conexion: Connection) -> None:
    """«Clase todos los días»: siete bloques, de lunes a domingo, a las 07:00 con 10 min de tolerancia."""
    conexion.execute(
        text("INSERT INTO horario (id, nombre) VALUES (:id, :nombre) ON CONFLICT (id) DO UPDATE SET nombre = :nombre"),
        {"id": HORARIO_ID, "nombre": HORARIO},
    )
    conexion.execute(text("DELETE FROM horario_bloque WHERE horario_id = :id"), {"id": HORARIO_ID})
    for dia in range(1, 8):
        conexion.execute(
            text(
                "INSERT INTO horario_bloque (horario_id, dia, hora_inicio, tolerancia_min) "
                "VALUES (:id, :dia, :hora, :tolerancia)"
            ),
            {"id": HORARIO_ID, "dia": dia, "hora": HORA_DE_CLASE, "tolerancia": TOLERANCIA_MIN},
        )


def _asegurar_camara(conexion: Connection) -> bool:
    """La cámara entrada: si existe, se usa sin tocarla. Si no, se crea y su token no se muestra. True si la creó."""
    existe = conexion.execute(text("SELECT 1 FROM dispositivo WHERE codigo = :codigo"), {"codigo": CAMARA}).first()
    if existe is not None:
        return False
    camaras.crear(conexion, DispositivoNuevo(codigo=CAMARA, nombre="Entrada", tipo="simulador"))
    return True


def _crear_personas(conexion: Connection, ahora: datetime) -> None:
    version = texto_vigente().version
    for persona in PERSONAS:
        conexion.execute(
            text(
                "INSERT INTO persona (id, documento, nombre, rol, horario_id, activa) "
                "VALUES (:id, :documento, :nombre, :rol, :horario_id, :activa)"
            ),
            {
                "id": persona.id,
                "documento": persona.documento,
                "nombre": persona.nombre,
                "rol": persona.rol,
                "horario_id": HORARIO_ID if persona.con_horario else None,
                "activa": persona.activa,
            },
        )
        # Todos con consentimiento vigente, en papel, de hace una semana (antes de sus eventos).
        conexion.execute(
            text(
                "INSERT INTO consentimiento (persona_id, version_texto, medio, aceptado_en) "
                "VALUES (:persona_id, :version, 'papel', :aceptado_en)"
            ),
            {"persona_id": persona.id, "version": version, "aceptado_en": ahora - timedelta(days=7)},
        )


def _crear_eventos(conexion: Connection, ahora: datetime) -> int:
    """Los eventos en orden de hora; cada permitido registra la llegada con R5 si es la primera del día."""
    llegadas = 0
    for evento in sorted(EVENTOS, key=lambda evento: evento.momento(ahora)):
        momento = evento.momento(ahora)
        persona_id = POR_DOCUMENTO[evento.documento].id if evento.documento else None
        conexion.execute(
            text(
                "INSERT INTO evento_acceso (id, fecha_hora, dispositivo_codigo, persona_id, resultado, motivo, "
                "similitud) VALUES (:id, :fecha_hora, :camara, :persona_id, :resultado, :motivo, :similitud)"
            ),
            {
                "id": evento.id,
                "fecha_hora": momento,
                "camara": CAMARA,
                "persona_id": persona_id,
                "resultado": evento.resultado,
                "motivo": evento.motivo,
                "similitud": evento.similitud,
            },
        )
        if evento.resultado == "permitido" and persona_id is not None:
            if registrar_llegada(conexion, persona_id, momento, "camara", evento_id=evento.id) is not None:
                llegadas += 1
    return llegadas


def crear(conexion: Connection, *, con_datos_reales: bool = False) -> Resultado:
    """Crea (o reemplaza) los datos de la evaluación con las fechas de hoy, y revisa las preguntas 1 a 9.

    Si hay datos que no son suyos y no se pide con_datos_reales, no escribe nada.
    """
    ajenos = datos_ajenos(conexion)
    if ajenos and not con_datos_reales:
        raise ErrorDeSemilla(
            f"La base ya tiene datos que no son de la semilla: {_contar(ajenos.personas, 'persona', 'personas')} y "
            f"{_contar(ajenos.eventos, 'evento', 'eventos')} "
            "(por ejemplo, los del Hito 1). La semilla nunca los cambia, pero las preguntas 2, 4 y 6 de la "
            "evaluación cuentan a todos y su respuesta puede cambiar. Para agregarla igual: "
            "accesia semilla agente --con-datos-reales"
        )
    _revisar_conflictos(conexion)
    borrar(conexion)

    ahora = tiempo.ahora()
    _crear_horario(conexion)
    camara_creada = _asegurar_camara(conexion)
    _crear_personas(conexion, ahora)
    llegadas = _crear_eventos(conexion, ahora)
    return Resultado(
        hoy=ahora.date(),
        personas=len(PERSONAS),
        eventos=len(EVENTOS),
        llegadas=llegadas,
        camara_creada=camara_creada,
        ajenos=ajenos,
        revision=revisar(conexion),
    )


# --- Lo que muestra el comando ---


def describir(resultado: Resultado) -> list[str]:
    """Las líneas que muestra «accesia semilla agente» al terminar."""
    lineas = [
        f"Semilla del agente lista para hoy, {resultado.hoy.isoformat()} (hora de Colombia): "
        f"{resultado.personas} personas (documentos SEMILLA-01 a SEMILLA-06), el horario «{HORARIO}» y "
        f"{resultado.eventos} eventos en la cámara {CAMARA}, con {resultado.llegadas} llegadas.",
    ]
    if resultado.camara_creada:
        lineas.append(
            f"La cámara {CAMARA} no existía: la creé sin mostrar su token. Si la vas a usar, cámbiale el token en la web."
        )
    if resultado.ajenos:
        lineas.append(
            f"La base también tiene {_contar(resultado.ajenos.personas, 'persona', 'personas')} y "
            f"{_contar(resultado.ajenos.eventos, 'evento', 'eventos')} que no son de la semilla: no los toqué."
        )
    bien = sum(revisada.coincide for revisada in resultado.revision)
    lineas.append(f"Preguntas 1 a 9 con las herramientas: {bien} de {len(resultado.revision)} como dice el contrato.")
    lineas += [_linea(revisada) for revisada in resultado.revision]
    lineas.append("Para borrarla: accesia semilla agente --borrar")
    return lineas


def _linea(revisada: Revisada) -> str:
    pregunta = revisada.pregunta
    if revisada.coincide:
        return f"  ✓ {pregunta.numero}. {pregunta.texto} {revisada.obtenido}"
    return (
        f"  ✗ {pregunta.numero}. {pregunta.texto} El contrato espera «{pregunta.esperado}»; con los datos de ahora, "
        f"{pregunta.herramienta} da «{revisada.obtenido}»."
    )


def describir_borrado(borrado: Borrado) -> list[str]:
    horario = f" y el horario «{HORARIO}»" if borrado.horario else ""
    return [
        f"Semilla del agente borrada: {_contar(borrado.personas, 'persona', 'personas')}, "
        f"{_contar(borrado.eventos, 'evento', 'eventos')}{horario}. La cámara "
        f"{CAMARA} y los datos que no eran de la semilla quedan como estaban."
    ]
