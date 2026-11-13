"""
Nombre: test_servidor_mcp.py
Descripción: Pruebas del servidor MCP del agente: «RF-08 · C1» con un cliente MCP real por Streamable HTTP, y «contrato agente · host» con el encabezado Host de mcp:8001, del portátil y de MCP_HOSTS_PERMITIDOS.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import json
import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import anyio
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import Engine
from starlette.testclient import TestClient

from accesia import servidor_mcp
from accesia.config import Configuracion

HERRAMIENTAS = {"buscar_persona", "asistencia_del_dia", "llegadas_tarde", "accesos_de_persona",
                "desconocidos_recientes"}
INICIAR = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "prueba", "version": "1"}},
}
ENCABEZADOS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


# --- Encabezado Host (contrato agente · host) ---


# Los hosts que acepta «accesia mcp» con MCP_HOSTS_PERMITIDOS por defecto (192.168.137.1:8001).
POR_DEFECTO = servidor_mcp.hosts_permitidos(
    Configuracion(database_url="postgresql://agente@localhost/accesia").hosts_mcp_extra
)


def _iniciar(motor: Engine, hosts: list[str], host: str, **encabezados: str) -> int:
    """Un initialize con ese Host. Cada vez una app nueva: su gestor de sesiones arranca una sola vez."""
    with TestClient(servidor_mcp.crear_app(motor, hosts), base_url=f"http://{host}") as cliente:
        return cliente.post("/mcp", json=INICIAR, headers={**ENCABEZADOS, **encabezados}).status_code


@pytest.mark.marca("contrato agente · host")
@pytest.mark.parametrize("host", ["mcp:8001", "192.168.137.1:8001", "localhost:8001", "127.0.0.1:8001"])
def test_acepta_el_host_de_docker_del_portatil_y_del_equipo(motor_agente: Engine, host: str) -> None:
    assert _iniciar(motor_agente, POR_DEFECTO, host) == 200


@pytest.mark.marca("contrato agente · host")
@pytest.mark.parametrize("host", ["otra:8001", "mcp:8000", "192.168.137.2:8001", "evil.example"])
def test_rechaza_otro_host_con_421(motor_agente: Engine, host: str) -> None:
    """La protección contra DNS rebinding del SDK: un Host que no está en la lista responde 421."""
    assert _iniciar(motor_agente, POR_DEFECTO, host) == 421


@pytest.mark.marca("contrato agente · host")
def test_rechaza_un_navegador_con_origin(motor_agente: Engine) -> None:
    assert _iniciar(motor_agente, POR_DEFECTO, "mcp:8001", Origin="http://192.168.137.1:8123") == 403


@pytest.mark.marca("contrato agente · host")
def test_mcp_hosts_permitidos_suma_hosts_sin_repetir() -> None:
    config = Configuracion(database_url="postgresql://agente@localhost/accesia",
                           mcp_hosts_permitidos=" 10.0.0.2:8001 , ,192.168.137.1:8001,mcp:8001")

    assert config.hosts_mcp_extra == ["10.0.0.2:8001", "192.168.137.1:8001", "mcp:8001"]
    assert servidor_mcp.hosts_permitidos(config.hosts_mcp_extra) == [
        "mcp:8001", "localhost:8001", "127.0.0.1:8001", "10.0.0.2:8001", "192.168.137.1:8001"
    ]
    assert Configuracion(database_url="postgresql://agente@localhost/accesia").hosts_mcp_extra == ["192.168.137.1:8001"]


@pytest.mark.marca("contrato agente · host")
def test_otro_host_de_mcp_hosts_permitidos(motor_agente: Engine) -> None:
    hosts = servidor_mcp.hosts_permitidos(["10.42.0.1:8001"])

    assert _iniciar(motor_agente, hosts, "10.42.0.1:8001") == 200
    assert _iniciar(motor_agente, hosts, "192.168.137.1:8001") == 421


# --- Un cliente MCP real (RF-08 · C1) ---


def _puerto_libre() -> int:
    with socket.socket() as libre:
        libre.bind(("127.0.0.1", 0))
        return libre.getsockname()[1]


@pytest.fixture(scope="module")
def url_mcp(semilla_confirmada: Engine) -> Iterator[str]:
    """El servidor MCP en uvicorn, en un hilo, con la semilla y el usuario agente."""
    puerto = _puerto_libre()
    app = servidor_mcp.crear_app(semilla_confirmada, servidor_mcp.hosts_permitidos([f"127.0.0.1:{puerto}"]))
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning"))
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    limite = time.monotonic() + 10
    while not servidor.started and time.monotonic() < limite:
        time.sleep(0.05)
    assert servidor.started, "uvicorn no arrancó"
    yield f"http://127.0.0.1:{puerto}/mcp"
    servidor.should_exit = True
    hilo.join(5)


def _como_el_cliente(url: str, llamadas: list[tuple[str, dict[str, Any]]]) -> tuple[Any, list[Any]]:
    """Lista las herramientas y las llama como lo hace un cliente MCP, por Streamable HTTP."""

    async def usar() -> tuple[Any, list[Any]]:
        async with streamable_http_client(url) as (leer, escribir), ClientSession(leer, escribir) as sesion:
            await sesion.initialize()
            lista = await sesion.list_tools()
            resultados = [await sesion.call_tool(nombre, argumentos) for nombre, argumentos in llamadas]
            return lista, resultados

    return anyio.run(usar)


def _texto(resultado: Any) -> dict[str, Any]:
    """Lo que lee el modelo: el JSON del primer contenido de texto."""
    assert not resultado.is_error
    return json.loads(resultado.content[0].text)


@pytest.mark.marca("RF-08 · C1")
def test_un_cliente_mcp_lista_las_cinco_herramientas(url_mcp: str) -> None:
    lista, _ = _como_el_cliente(url_mcp, [])
    herramientas = {herramienta.name: herramienta for herramienta in lista.tools}

    assert set(herramientas) == HERRAMIENTAS
    for herramienta in herramientas.values():
        assert herramienta.description and " " in herramienta.description  # en español, para el modelo
        assert herramienta.annotations.read_only_hint is True
        assert herramienta.annotations.destructive_hint is False
    parametros = {nombre: set(herramienta.input_schema["properties"]) for nombre, herramienta in herramientas.items()}
    assert parametros == {
        "buscar_persona": {"nombre"},
        "asistencia_del_dia": {"fecha"},
        "llegadas_tarde": {"desde", "hasta"},
        "accesos_de_persona": {"nombre", "desde", "hasta"},
        "desconocidos_recientes": {"horas"},
    }
    assert herramientas["desconocidos_recientes"].input_schema["properties"]["horas"]["type"] == "integer"
    assert herramientas["buscar_persona"].input_schema["required"] == ["nombre"]


@pytest.mark.marca("RF-08 · C1")
def test_un_cliente_mcp_llama_las_cinco_herramientas(url_mcp: str) -> None:
    _, resultados = _como_el_cliente(url_mcp, [
        ("buscar_persona", {"nombre": "Elena Mora"}),
        ("asistencia_del_dia", {"fecha": "ayer"}),
        ("llegadas_tarde", {"desde": "antier", "hasta": "ayer"}),
        ("accesos_de_persona", {"nombre": "Ana", "desde": "ayer", "hasta": "ayer"}),
        ("desconocidos_recientes", {}),
    ])
    persona, asistencia, tardes, accesos, desconocidos = (_texto(resultado) for resultado in resultados)

    assert persona == {"personas": [{"nombre": "Elena Mora", "rol": "estudiante", "activa": False,
                                     "horario": "Clase todos los días"}]}
    assert asistencia["tarde"] == [{"nombre": "Carla Ruiz", "llegada": "07:12", "minutos_tarde": 12}]
    assert asistencia["ausentes"] == ["Felipe Soto"]
    assert asistencia["total_llegadas"] == 4
    assert tardes["total"] == 3
    assert accesos["total"] == 2
    assert desconocidos == {"horas": 24, "total": 3, "por_camara": {"entrada": 3}, "ultimos": ["2026-11-20 08:00"] * 3}
    assert resultados[1].structured_content == asistencia  # también como contenido estructurado


@pytest.mark.marca("RF-08 · C1")
def test_un_error_vuelve_como_texto_y_no_como_excepcion(url_mcp: str) -> None:
    _, [fecha, horas] = _como_el_cliente(url_mcp, [
        ("asistencia_del_dia", {"fecha": "el lunes"}),
        ("desconocidos_recientes", {"horas": 500}),
    ])

    assert set(_texto(fecha)) == {"error"}
    assert set(_texto(horas)) == {"error"}
