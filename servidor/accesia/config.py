"""
Nombre: config.py
Descripción: Configuración del servidor de AccesIA, leída del entorno (variables de specs/arquitectura.md).
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """Variables del servidor. Docker Compose las toma de infra/.env y arma DATABASE_URL y MQTT_URL."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    database_url: str
    mqtt_url: str | None = None
    agente_db_password: SecretStr | None = None
    sesion_secreto: SecretStr | None = None
    admin_correo: str | None = None
    admin_clave_inicial: SecretStr | None = None

    # Reglas (specs/reglas.md); se cambian en infra/.env y se reinicia el servidor (D-14).
    umbral_similitud: float = Field(default=0.363, ge=-1, le=1)
    ventana_repetido_s: int = Field(default=60, ge=0)
    alerta_desconocidos: int = Field(default=3, ge=1)
    alerta_ventana_s: int = Field(default=60, ge=1)
    inscripcion_muestras: int = Field(default=5, ge=1, le=20)
    inscripcion_vence_s: int = Field(default=120, ge=1)
    cara_min_px: int = Field(default=80, ge=1)
    nitidez_min: float = Field(default=60, ge=0)
    zona_horaria: str = "America/Bogota"
    ollama_modelo: str = "qwen2.5:3b"

    # Servidor MCP del agente: encabezados Host que acepta además de mcp:8001, separados por comas. En el
    # escenario 2 (D-21), Home Assistant OS lo llama por la IP del portátil en el hotspot.
    mcp_hosts_permitidos: str = "192.168.137.1:8001"

    @field_validator("database_url")
    @classmethod
    def usar_psycopg(cls, valor: str) -> str:
        """Acepta postgresql:// y lo pasa al controlador psycopg 3 de SQLAlchemy."""
        if valor.startswith("postgresql://"):
            return "postgresql+psycopg://" + valor.removeprefix("postgresql://")
        return valor

    @field_validator("zona_horaria")
    @classmethod
    def zona_existente(cls, valor: str) -> str:
        try:
            ZoneInfo(valor)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"La zona horaria «{valor}» no existe.") from error
        return valor

    @property
    def zona(self) -> ZoneInfo:
        """Zona de Colombia para fechas y horas (R8)."""
        return ZoneInfo(self.zona_horaria)

    @property
    def hosts_mcp_extra(self) -> list[str]:
        """MCP_HOSTS_PERMITIDOS como lista, sin espacios ni elementos vacíos."""
        return [host.strip() for host in self.mcp_hosts_permitidos.split(",") if host.strip()]


@lru_cache
def configuracion() -> Configuracion:
    """Configuración del proceso, leída una sola vez."""
    return Configuracion()
