"""
Nombre: cache_del_prompt.py
Descripción: Mide con prompt_eval_count de Ollama qué parte del prompt del agente se reutiliza entre preguntas, con cada pedido armado como lo arma Home Assistant: antes (mcp-agente.md 1.4, con la hora en el prompt) y después (1.5, con fecha_y_hora_GetDateTime).
Fecha de creación: 2026-11-13
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.0

Uso, desde servidor/, con Ollama en http://127.0.0.1:11434 (por ejemplo, en Docker y solo con CPU) y el modelo ya
descargado:

    uv run python scripts/cache_del_prompt.py --modelo qwen2.5:1.5b

Así arma Home Assistant cada pedido a Ollama (rama dev de home-assistant/core, noviembre de 2026):
- conversation/chat_log.py: el prompt de sistema une con saltos de línea las instrucciones del agente, el texto de la
  API de las herramientas y, si ninguna herramienta tiene un nombre que termina en «GetDateTime», la línea
  DATE_TIME_PROMPT de helpers/llm.py, con la hora y sus segundos;
- mcp/__init__.py: el texto de la API es «The following tools are available from a remote server named {name}.»;
- mcp/coordinator.py y ollama/entity.py: el esquema de cada herramienta pasa por probatio.from_openapi y
  probatio.to_openapi (OpenAPI 3.1.0), y va como {"type": "function", "function": {name, parameters, description}};
- ollama/entity.py: el mensaje de sistema va primero, con keep_alive -1 y num_ctx 8192.

Cada pregunta va en una conversación nueva, como cuando alguien abre Assist, unos segundos después de la anterior.
El script no llama las herramientas: mira el primer pedido de cada pregunta y qué herramienta pide el modelo.

En Ollama 0.40, prompt_eval_count cuenta todo el prompt y prompt_eval_cached_count, la parte que salió de la caché:
lo que se procesó de verdad es la resta. En versiones anteriores sin prompt_eval_cached_count, prompt_eval_count ya
era solo lo procesado. Conviene medir con Ollama recién arrancado: llama-server también guarda en RAM prompts de
pedidos anteriores, y una segunda corrida encuentra en la caché hasta la primera pregunta.
"""

import argparse
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import anyio
import httpx
import probatio
from sqlalchemy import create_engine

from accesia import servidor_mcp

CONTRATO = Path(__file__).resolve().parents[2] / "specs" / "contratos" / "mcp-agente.md"
ZONA = ZoneInfo("America/Bogota")
API_PROMPT = "The following tools are available from a remote server named {name}."  # mcp/__init__.py
LINEA_DE_LA_HORA = "Current time is {hora}. Today's date is {fecha}.\n"  # DATE_TIME_PROMPT de helpers/llm.py
NUM_CTX = 8192  # DEFAULT_NUM_CTX de ollama/const.py
PREGUNTAS = ("¿Quién llegó tarde ayer?", "¿Qué hora es?", "¿Hubo desconocidos en las últimas 24 horas?")
REUTILIZA = 0.2  # una pregunta reutiliza el comienzo si procesa menos de esta parte de lo que procesó la primera
Fila = tuple[str, str, int, int, float, str]  # escenario, pregunta, prompt, de la caché, milisegundos, herramienta

# Las instrucciones de mcp-agente.md 1.4, con su línea de la hora; la 1.5 la quitó.
INSTRUCCIONES_14 = "\n".join([
    "Eres el asistente de la portería de AccesIA. Respondes en español, en una o dos frases.",
    "Hoy es {fecha} y son las {hora} en Colombia.",
    "Para cualquier dato sobre personas, llegadas, tardanzas, accesos o desconocidos, usa las herramientas de "
    "AccesIA. Nunca inventes nombres, horas ni cifras: si una herramienta no devuelve datos, dilo.",
    "A las herramientas les puedes pasar fechas como AAAA-MM-DD o las palabras hoy, ayer o antier.",
    "No puedes abrir puertas, inscribir personas ni cambiar datos. Si te lo piden, explica que eso se hace en la web "
    "de administración de AccesIA.",
    "No reveles documentos de identidad ni datos de contacto.",
])


def instrucciones_del_contrato() -> str:
    """Las instrucciones de mcp-agente.md tal como están: se mide lo que dice el contrato."""
    seccion = CONTRATO.read_text(encoding="utf-8").split("## Instrucciones del agente", 1)[1]
    return seccion.split("```text\n", 1)[1].split("```", 1)[0].strip()


def herramientas_como_home_assistant() -> list[dict[str, Any]]:
    """Las herramientas del servidor MCP como las manda a Ollama la integración de Home Assistant."""
    motor = create_engine("postgresql+psycopg://nadie@127.0.0.1:1/nada")  # listar las herramientas no toca la base
    herramientas = []
    for herramienta in anyio.run(servidor_mcp.crear_servidor(motor).list_tools):
        esquema = probatio.to_openapi(probatio.from_openapi(herramienta.input_schema), openapi_version="3.1.0")
        funcion: dict[str, Any] = {"name": herramienta.name, "parameters": esquema}
        if herramienta.description:
            funcion["description"] = herramienta.description
        herramientas.append({"type": "function", "function": funcion})
    return herramientas


def prompt_de_sistema(instrucciones: str, herramientas: list[dict[str, Any]], ahora: datetime) -> str:
    """El prompt de sistema en el orden de conversation/chat_log.py."""
    partes = [instrucciones, API_PROMPT.format(name=servidor_mcp.NOMBRE)]
    if not any(herramienta["function"]["name"].endswith("GetDateTime") for herramienta in herramientas):
        partes.append(LINEA_DE_LA_HORA.format(hora=ahora.strftime("%H:%M:%S"), fecha=ahora.strftime("%Y-%m-%d")))
    return "\n".join(partes)


def preguntar(cliente: httpx.Client, modelo: str, sistema: str, herramientas: list[dict[str, Any]],
              pregunta: str) -> dict[str, Any]:
    """Un pedido como el de ollama/entity.py, sin stream: la respuesta trae prompt_eval_count."""
    respuesta = cliente.post("/api/chat", json={
        "model": modelo,
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": pregunta}],
        "tools": herramientas,
        "stream": False,
        "keep_alive": -1,
        "options": {"num_ctx": NUM_CTX},
        "think": False,
    })
    respuesta.raise_for_status()
    return respuesta.json()


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.split("\n", 7)[2].removeprefix("Descripción: "))
    analizador.add_argument("--ollama", default="http://127.0.0.1:11434", help="URL de Ollama")
    analizador.add_argument("--modelo", default="qwen2.5:1.5b", help="modelo ya descargado en Ollama")
    analizador.add_argument("--pausa", type=float, default=3.0, help="segundos entre una pregunta y la siguiente")
    argumentos = analizador.parse_args()

    todas = herramientas_como_home_assistant()
    sin_fecha = [herramienta for herramienta in todas if not herramienta["function"]["name"].endswith("GetDateTime")]
    escenarios: list[tuple[str, Callable[[datetime], str], list[dict[str, Any]]]] = [
        ("antes (1.4)", lambda ahora: INSTRUCCIONES_14.format(fecha=ahora.strftime("%Y-%m-%d"),
                                                             hora=ahora.strftime("%H:%M")), sin_fecha),
        ("después (1.5)", lambda _ahora: instrucciones_del_contrato(), todas),
    ]

    filas: list[Fila] = []
    with httpx.Client(base_url=argumentos.ollama, timeout=900) as cliente:
        # Carga el modelo antes de medir, para que la primera pregunta no cuente la carga.
        preguntar(cliente, argumentos.modelo, "Responde con una palabra.", [], "Hola")
        for escenario, instrucciones, herramientas in escenarios:
            for pregunta in PREGUNTAS:
                ahora = datetime.now(ZONA)
                datos = preguntar(cliente, argumentos.modelo, prompt_de_sistema(instrucciones(ahora), herramientas, ahora),
                                  herramientas, pregunta)
                pedidas = [llamada["function"]["name"] for llamada in datos["message"].get("tool_calls") or []]
                filas.append((escenario, pregunta, datos.get("prompt_eval_count", 0),
                              datos.get("prompt_eval_cached_count", 0), datos.get("prompt_eval_duration", 0) / 1e6,
                              ", ".join(pedidas) or "ninguna"))
                time.sleep(argumentos.pausa)

    print(f"Modelo {argumentos.modelo} en {argumentos.ollama}; {len(todas)} herramientas en la 1.5 y {len(sin_fecha)} "
          "en la 1.4.\n")
    print(f"{'Escenario':<14} {'Pregunta':<44} {'Prompt':>7} {'Caché':>6} {'Procesados':>10} {'Tiempo (ms)':>11}  "
          "Herramienta pedida")
    for escenario, pregunta, prompt, cache, milisegundos, pedidas in filas:
        print(f"{escenario:<14} {pregunta:<44} {prompt:>7} {cache:>6} {prompt - cache:>10} {milisegundos:>11.0f}  "
              f"{pedidas}")

    reutiliza = {}
    for escenario, *_ in escenarios:
        primera, *siguientes = [prompt - cache for nombre, _, prompt, cache, *_ in filas if nombre == escenario]
        reutiliza[escenario] = all(procesados < primera * REUTILIZA for procesados in siguientes)
        veredicto = "reutilizan" if reutiliza[escenario] else "no reutilizan"
        print(f"\n{escenario}: la primera pregunta procesa {primera} tokens; las siguientes, "
              f"{' y '.join(str(procesados) for procesados in siguientes)}: {veredicto} las instrucciones y las "
              "herramientas.")
    return 0 if reutiliza["después (1.5)"] else 1


if __name__ == "__main__":
    sys.exit(principal())
