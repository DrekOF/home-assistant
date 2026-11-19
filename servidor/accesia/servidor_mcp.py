"""
Nombre: servidor_mcp.py
Descripción: Servidor MCP del agente (contratos/mcp-agente.md): «AccesIA», Streamable HTTP en /mcp, puerto 8001, las seis herramientas de solo lectura con el usuario agente (D-15) y sin autenticación (D-16).
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.1

Usa el SDK oficial mcp 2.x, donde FastMCP se llama MCPServer. Lo arranca el comando «accesia mcp» en el servicio
mcp de Docker Compose, con la misma imagen del servidor.

- Sin sesiones (stateless_http) y con respuestas JSON: cada pedido es independiente, así que si el contenedor se
  reinicia, Home Assistant no queda con una sesión vieja.
- El SDK valida el encabezado Host contra DNS rebinding. Acepta mcp:8001, localhost:8001 y 127.0.0.1:8001, y los
  de MCP_HOSTS_PERMITIDOS (por defecto 192.168.137.1:8001, la IP del portátil en el hotspot, D-21). Un pedido con
  encabezado Origin (un navegador) se rechaza.
"""

import logging
import sys
from collections.abc import Sequence
from typing import Annotated, Any

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from starlette.applications import Starlette

from accesia import agente
from accesia.config import configuracion
from accesia.registro import configurar_registro

registro = logging.getLogger(__name__)

NOMBRE = "AccesIA"
RUTA = "/mcp"
ESCUCHA = "0.0.0.0"
PUERTO = 8001
USUARIO_AGENTE = "agente"
# mcp:8001 es la dirección dentro de la red de Docker; localhost y 127.0.0.1, la del healthcheck y las pruebas.
HOSTS_FIJOS = (f"mcp:{PUERTO}", f"localhost:{PUERTO}", f"127.0.0.1:{PUERTO}")

SOLO_LECTURA = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True,
                               open_world_hint=False)

# Descripciones en español: el modelo las lee (mcp-agente.md, Reglas para todas las herramientas).
FECHA = "Fecha como AAAA-MM-DD, o las palabras hoy, ayer o antier (en hora de Colombia)."
NOMBRE_O_PARTE = "Nombre o parte del nombre de la persona, de 2 a 60 caracteres; no importan tildes ni mayúsculas."

# Home Assistant no agrega al prompt su línea de fecha y hora si alguna herramienta tiene un nombre que termina en
# «GetDateTime» (conversation/chat_log.py). Esa línea cambia cada segundo y no deja que Ollama reutilice entre
# preguntas el comienzo del prompt, con las herramientas (mcp-agente.md 1.5, D-22). Por eso el sufijo va en inglés.
FECHA_Y_HORA = "fecha_y_hora_GetDateTime"


def hosts_permitidos(extra: Sequence[str] = ()) -> list[str]:
    """Los encabezados Host que acepta el servidor: los fijos y los de MCP_HOSTS_PERMITIDOS, sin repetir."""
    return list(dict.fromkeys([*HOSTS_FIJOS, *extra]))


def crear_servidor(motor: Engine) -> MCPServer:
    """El servidor «AccesIA» con las seis herramientas del contrato, todas de solo lectura."""
    herramientas = agente.Herramientas(motor)
    # log_level WARNING: el SDK configura el registro raíz con basicConfig; así solo deja pasar avisos.
    servidor = MCPServer(NOMBRE, log_level="WARNING")

    @servidor.tool(
        name="buscar_persona",
        description="Busca personas registradas en AccesIA por su nombre o parte del nombre, sin importar tildes ni "
        "mayúsculas. Dice su rol, si está activa (si puede entrar) y su horario. Devuelve hasta 10 personas.",
        annotations=SOLO_LECTURA,
    )
    def buscar_persona(nombre: Annotated[str, Field(description=NOMBRE_O_PARTE)]) -> dict[str, Any]:
        return herramientas.buscar_persona(nombre)

    @servidor.tool(
        name="asistencia_del_dia",
        description="Dice quién llegó a tiempo, quién llegó tarde (con los minutos de retraso), quién llegó sin "
        "horario y quién faltó en una fecha. Las horas van en hora de Colombia.",
        annotations=SOLO_LECTURA,
    )
    def asistencia_del_dia(
        fecha: Annotated[str, Field(description=f"{FECHA} Por defecto, hoy.")] = "hoy",
    ) -> dict[str, Any]:
        return herramientas.asistencia_del_dia(fecha)

    @servidor.tool(
        name="llegadas_tarde",
        description="Lista las llegadas tarde entre dos fechas, incluidas, con los minutos de retraso de cada una.",
        annotations=SOLO_LECTURA,
    )
    def llegadas_tarde(
        desde: Annotated[str, Field(description=f"{FECHA} Por defecto, hoy.")] = "hoy",
        hasta: Annotated[str, Field(description=f"{FECHA} Como máximo 31 días después de desde. Por defecto, hoy.")]
        = "hoy",
    ) -> dict[str, Any]:
        return herramientas.llegadas_tarde(desde, hasta)

    @servidor.tool(
        name="accesos_de_persona",
        description="Lista los intentos de entrada de una persona entre dos fechas: fecha, hora, cámara y resultado. "
        "Si el nombre coincide con varias personas, devuelve sus nombres para preguntar cuál.",
        annotations=SOLO_LECTURA,
    )
    def accesos_de_persona(
        nombre: Annotated[str, Field(description=NOMBRE_O_PARTE)],
        desde: Annotated[str, Field(description=f"{FECHA} Por defecto, hoy.")] = "hoy",
        hasta: Annotated[str, Field(description=f"{FECHA} Por defecto, hoy.")] = "hoy",
    ) -> dict[str, Any]:
        return herramientas.accesos_de_persona(nombre, desde, hasta)

    @servidor.tool(
        name="desconocidos_recientes",
        description="Cuenta las caras desconocidas de las últimas horas, por cámara, con la hora de las más recientes.",
        annotations=SOLO_LECTURA,
    )
    def desconocidos_recientes(
        horas: Annotated[int, Field(description="Cuántas horas hacia atrás, de 1 a 168. Por defecto, 24.")] = 24,
    ) -> dict[str, Any]:
        return herramientas.desconocidos_recientes(horas)

    @servidor.tool(
        name=FECHA_Y_HORA,
        description="Dice la fecha, el día de la semana y la hora actuales en Colombia. Úsala solo si la pregunta "
        "necesita la fecha o la hora exacta; para hoy, ayer o antier no hace falta.",
        annotations=SOLO_LECTURA,
    )
    def fecha_y_hora() -> dict[str, Any]:
        return herramientas.fecha_y_hora()

    return servidor


def crear_app(motor: Engine, hosts: Sequence[str]) -> Starlette:
    """La app ASGI de Streamable HTTP en /mcp, sin sesiones, con respuestas JSON y el Host validado."""
    seguridad = TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=list(hosts), allowed_origins=[]
    )
    return crear_servidor(motor).streamable_http_app(
        streamable_http_path=RUTA,
        json_response=True,
        stateless_http=True,
        transport_security=seguridad,
        host=ESCUCHA,
    )


def motor_del_agente(url: str) -> Engine:
    """El motor de la base del servidor MCP: el usuario agente, que solo lee las tres vistas (D-15)."""
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})


def usuario_de(url: str) -> str | None:
    try:
        return make_url(url).username
    except ArgumentError:
        return None


def correr() -> int:
    """El comando «accesia mcp»: solo arranca con el usuario agente de la base (D-15)."""
    config = configuracion()
    usuario = usuario_de(config.database_url)
    if usuario != USUARIO_AGENTE:
        print(
            f"El servidor MCP solo se conecta a la base con el usuario «{USUARIO_AGENTE}» (D-15), y DATABASE_URL usa "
            f"«{usuario or 'ninguno'}». En Docker Compose, el servicio mcp ya la arma con AGENTE_DB_PASSWORD.",
            file=sys.stderr,
        )
        return 1
    configurar_registro()
    logging.getLogger("accesia").propagate = False  # el SDK agrega un manejador raíz: sin esto, cada línea sale dos veces
    hosts = hosts_permitidos(config.hosts_mcp_extra)
    app = crear_app(motor_del_agente(config.database_url), hosts)
    registro.info("Servidor MCP «%s» en http://%s:%d%s. Acepta el Host de %s.", NOMBRE, ESCUCHA, PUERTO, RUTA,
                  ", ".join(hosts))
    uvicorn.run(app, host=ESCUCHA, port=PUERTO, log_level="info")
    return 0
