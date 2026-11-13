"""
Nombre: esquemas.py
Descripción: Esquemas de la API de AccesIA con pydantic, iguales a los de specs/contratos/openapi.yaml 1.3 (sesión, personas, consentimiento, horarios, cámaras, inscripciones, la respuesta a la cámara, huellas, accesos, asistencia y configuración).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
"""

from datetime import date, datetime
from typing import Annotated, ClassVar, Literal, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    AnyUrl,
    AwareDatetime,
    BaseModel,
    EmailStr,
    Field,
    PlainSerializer,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from accesia.tiempo import a_colombia

# --- Tipos comunes ---

# Toda fecha y hora sale en ISO 8601 con la zona de Colombia y sin microsegundos (R8).
FechaHora = Annotated[
    datetime, PlainSerializer(lambda valor: a_colombia(valor).isoformat(), return_type=str, when_used="json")
]

Rol = Literal["estudiante", "docente", "administrativo", "otro"]
Medio = Literal["web", "papel"]
TipoCamara = Literal["tinyml", "respaldo", "simulador"]
EstadoInscripcion = Literal["activa", "completada", "vencida", "cancelada"]
Modo = Literal["reconocer", "inscribir"]

Documento = Annotated[str, StringConstraints(pattern=r"^[0-9A-Za-z-]{3,20}$")]
NombrePersona = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
NombreCorto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
CodigoCamara = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{3,32}$")]
HoraInicio = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]

CODIGO_RESERVADO = "servidor"  # el de los temas MQTT del servidor (specs/contratos/mqtt.md)


def _url_valida(valor: str | None) -> str | None:
    """Comprueba que sea una URL con esquema y servidor, y la deja tal cual llegó."""
    if valor is not None:
        try:
            TypeAdapter(AnyUrl).validate_python(valor)
        except ValidationError:
            raise ValueError("La URL de captura no es válida (por ejemplo, http://10.42.0.30/capture).") from None
    return valor


UrlCaptura = Annotated[str | None, AfterValidator(_url_valida)]


class Cambios(BaseModel):
    """Base de los cuerpos PATCH: al menos un campo, y null solo en los campos que el contrato deja en null."""

    nulos_permitidos: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def revisar_cambios(self) -> Self:
        campos = self.model_fields_set
        if not campos:
            raise ValueError("Envía al menos un dato para cambiar.")
        nulos = sorted(campo for campo in campos if getattr(self, campo) is None and campo not in self.nulos_permitidos)
        if nulos:
            raise ValueError("No pueden quedar vacíos: " + ", ".join(f"«{campo}»" for campo in nulos) + ".")
        return self

    def valores(self) -> dict:
        """Solo los campos que llegaron en la petición."""
        return self.model_dump(exclude_unset=True)


# --- Sesión ---


class Credenciales(BaseModel):
    correo: EmailStr
    clave: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class Administrador(BaseModel):
    id: UUID
    correo: str
    nombre: str


# --- Personas ---


class PersonaCorta(BaseModel):
    id: UUID
    nombre: str


class Persona(BaseModel):
    id: UUID
    documento: str
    nombre: str
    rol: Rol
    horario_id: UUID | None
    horario_nombre: str | None
    activa: bool
    consentimiento_vigente: bool
    muestras: int
    creada: FechaHora
    actualizada: FechaHora


class PersonaNueva(BaseModel):
    documento: Documento
    nombre: NombrePersona
    rol: Rol = "estudiante"
    horario_id: UUID | None = None
    activa: bool = True


class PersonaCambios(Cambios):
    nulos_permitidos: ClassVar[frozenset[str]] = frozenset({"horario_id"})

    documento: Documento | None = None
    nombre: NombrePersona | None = None
    rol: Rol | None = None
    horario_id: UUID | None = None
    activa: bool | None = None


class PaginaPersonas(BaseModel):
    elementos: list[Persona]
    total: int
    pagina: int
    por_pagina: int


# --- Consentimiento ---


class Consentimiento(BaseModel):
    id: UUID
    persona_id: UUID
    version_texto: str
    medio: Medio
    registrado_por: str | None
    aceptado_en: FechaHora
    revocado_en: FechaHora | None


class ConsentimientoNuevo(BaseModel):
    version_texto: str
    medio: Medio = "web"
    acepta: Literal[True]
    aceptado_en: AwareDatetime | None = None


class TextoConsentimiento(BaseModel):
    version: str
    texto: str


# --- Horarios (D-20) ---


class HorarioBloque(BaseModel):
    dia: Annotated[int, Field(ge=1, le=7)]
    hora_inicio: HoraInicio
    tolerancia_min: Annotated[int, Field(ge=0, le=120)]


def _un_bloque_por_dia(bloques: list[HorarioBloque]) -> list[HorarioBloque]:
    dias = [bloque.dia for bloque in bloques]
    if len(dias) != len(set(dias)):
        raise ValueError("Cada día puede tener un solo bloque.")
    return sorted(bloques, key=lambda bloque: bloque.dia)


BloquesHorario = Annotated[list[HorarioBloque], Field(min_length=1, max_length=7), AfterValidator(_un_bloque_por_dia)]


class Horario(BaseModel):
    id: UUID
    nombre: str
    bloques: list[HorarioBloque]


class HorarioNuevo(BaseModel):
    nombre: NombreCorto
    bloques: BloquesHorario


class HorarioCambios(Cambios):
    nombre: NombreCorto | None = None
    bloques: BloquesHorario | None = None


# --- Cámaras ---


class InscripcionCorta(BaseModel):
    id: UUID
    muestras: int
    requeridas: int
    estado: EstadoInscripcion
    vence: FechaHora


# --- Inscripciones (R9) ---

MotivoMuestra = Literal[
    "sin_cara", "varias_caras", "cara_pequena", "borrosa", "parece_otra_persona", "distinta_de_la_primera"
]


class Inscripcion(BaseModel):
    id: UUID
    persona: PersonaCorta
    dispositivo: str
    estado: EstadoInscripcion
    muestras: int
    requeridas: int
    ultimo_motivo: MotivoMuestra | None
    creada: FechaHora
    vence: FechaHora
    terminada: FechaHora | None


class InscripcionNueva(BaseModel):
    persona_id: UUID
    dispositivo: CodigoCamara


# --- Cámara → servidor (specs/contratos/api-dispositivo.md) ---

ResultadoRostro = Literal[
    "permitido", "denegado", "desconocido", "descartado", "muestra_aceptada", "muestra_rechazada"
]
MotivoRostro = Literal[
    "inactiva",
    "sin_consentimiento",
    "bajo_umbral",
    "sin_cara",
    "varias_caras",
    "cara_pequena",
    "borrosa",
    "parece_otra_persona",
    "distinta_de_la_primera",
]


class RespuestaRostro(BaseModel):
    """Respuesta 200 a la cámara: todos los campos siempre presentes, con null cuando no aplica."""

    modo: Modo
    resultado: ResultadoRostro
    motivo: MotivoRostro | None
    persona: PersonaCorta | None
    similitud: float | None
    repetido: bool
    evento_id: UUID | None
    inscripcion: InscripcionCorta | None
    mensaje: str
    hora: FechaHora


class EstadoCamara(BaseModel):
    """Último estado que publicó la cámara por MQTT; llega el Día 3."""

    perfil: str | None = None
    firmware: str | None = None
    ip: str | None = None
    rssi: int | None = None
    psram_kb: int | None = None
    libre_kb: int | None = None
    segundos_encendida: int | None = None


class Dispositivo(BaseModel):
    codigo: str
    nombre: str
    tipo: TipoCamara
    url_captura: str | None
    activo: bool
    en_linea: bool
    modo: Modo
    inscripcion_activa: InscripcionCorta | None
    ultimo_contacto: FechaHora | None
    estado: EstadoCamara | None
    creado: FechaHora


class DispositivoConToken(Dispositivo):
    token: str


class DispositivoNuevo(BaseModel):
    codigo: CodigoCamara
    nombre: NombreCorto
    tipo: TipoCamara
    url_captura: UrlCaptura = None

    @field_validator("codigo")
    @classmethod
    def codigo_libre(cls, codigo: str) -> str:
        if codigo == CODIGO_RESERVADO:
            raise ValueError("El código «servidor» está reservado para los temas MQTT del servidor.")
        return codigo

    @model_validator(mode="after")
    def respaldo_con_url(self) -> Self:
        if self.tipo == "respaldo" and self.url_captura is None:
            raise ValueError("Una cámara de respaldo necesita su URL de captura.")
        return self


class DispositivoCambios(Cambios):
    nulos_permitidos: ClassVar[frozenset[str]] = frozenset({"url_captura"})

    nombre: NombreCorto | None = None
    tipo: TipoCamara | None = None
    url_captura: UrlCaptura = None
    activo: bool | None = None


# --- Huellas (RF-12 · C1): las muestras sin la huella ---


class RostroResumen(BaseModel):
    id: UUID
    fuente: TipoCamara
    modelo: str
    calidad: float | None
    creado: FechaHora


# --- Accesos (RF-05 · C3) ---

ResultadoAcceso = Literal["permitido", "denegado", "desconocido"]
MotivoAcceso = Literal["inactiva", "sin_consentimiento", "bajo_umbral"]


class EventoAcceso(BaseModel):
    id: UUID
    fecha_hora: FechaHora
    dispositivo: str
    resultado: ResultadoAcceso
    motivo: MotivoAcceso | None
    persona: PersonaCorta | None
    similitud: float | None


class PaginaEventos(BaseModel):
    elementos: list[EventoAcceso]
    total: int
    pagina: int
    por_pagina: int


# --- Asistencia (R5, RF-06) ---

EstadoAsistencia = Literal["a_tiempo", "tarde", "sin_horario"]
OrigenAsistencia = Literal["camara", "manual"]


class FilaAsistencia(BaseModel):
    persona: PersonaCorta
    llegada: FechaHora
    estado: EstadoAsistencia
    minutos_tarde: int | None
    origen: OrigenAsistencia
    registrado_por: str | None


class Asistencia(FilaAsistencia):
    """Una llegada con su fecha local (R8)."""

    fecha: date


class AsistenciaManualNueva(BaseModel):
    persona_id: UUID
    llegada: AwareDatetime


class ReporteAsistencia(BaseModel):
    fecha: date
    a_tiempo: list[FilaAsistencia]
    tarde: list[FilaAsistencia]
    sin_horario: list[FilaAsistencia]
    ausentes: list[PersonaCorta]
    total_llegadas: int


# --- Configuración (D-14) ---


class Configuracion(BaseModel):
    """Los valores de las reglas que usa el servidor. No es accesia.config.Configuracion, que los lee del entorno."""

    umbral_similitud: float
    ventana_repetido_s: int
    alerta_desconocidos: int
    alerta_ventana_s: int
    inscripcion_muestras: int
    inscripcion_vence_s: int
    cara_min_px: int
    nitidez_min: float
    zona_horaria: str
    modelo_deteccion: str
    modelo_huella: str
    version: str
