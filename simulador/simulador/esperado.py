"""
Nombre: esperado.py
Descripción: Respuestas esperadas del modo carpeta (esperado.json): cómo se leen, cómo se comparan con lo que respondió el servidor y el resumen.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Formato (simulador/README.md):

    { "fotos": {
        "ana-01.jpg": { "resultado": "permitido", "persona": "Ana Gómez" },
        "pared.jpg":  { "enviada": false } } }

Solo se comparan los campos escritos. `persona` se compara por nombre (o null). `"enviada": false` dice que la
foto no debe enviarse (sin cara o cara pequeña). Las fotos que no están en la lista se envían sin comparar.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from simulador.consola import contar, nombre_de
from simulador.envio import Respuesta

ARCHIVO_ESPERADO = "esperado.json"
CAMPOS_RESPUESTA = ("resultado", "motivo", "persona", "repetido", "modo")
CAMPOS = ("enviada", *CAMPOS_RESPUESTA)


class ErrorEsperado(Exception):
    """esperado.json no tiene el formato acordado."""


@dataclass(frozen=True)
class Obtenido:
    """Qué pasó con una foto: si se envió y la respuesta, o por qué no se envió (`nota`)."""

    enviada: bool
    respuesta: Respuesta | None = None
    nota: str = ""


def cargar_esperado(carpeta: Path) -> dict[str, dict[str, Any]] | None:
    """Las respuestas esperadas por nombre de foto, o None si la carpeta no trae esperado.json."""
    ruta = carpeta / ARCHIVO_ESPERADO
    if not ruta.exists():
        return None
    try:
        # utf-8-sig: el Bloc de notas y PowerShell 5.1 pueden guardar el archivo con BOM.
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise ErrorEsperado(f"{ruta} no es un JSON válido: {error}") from error

    fotos = datos.get("fotos") if isinstance(datos, dict) else None
    if not isinstance(fotos, dict):
        raise ErrorEsperado(f'{ruta} debe ser un objeto con "fotos": {{"nombre.jpg": {{...}}, ...}}')
    for nombre, esperado in fotos.items():
        if not isinstance(esperado, dict):
            raise ErrorEsperado(f"{ruta}: lo esperado de {nombre} debe ser un objeto")
        sobrantes = sorted(set(esperado) - set(CAMPOS))
        if sobrantes:
            raise ErrorEsperado(
                f"{ruta}: {nombre} tiene campos que no se comparan: {', '.join(sobrantes)}. "
                f"Los campos válidos son: {', '.join(CAMPOS)}"
            )
        if "enviada" in esperado and not isinstance(esperado["enviada"], bool):
            raise ErrorEsperado(f"{ruta}: en {nombre}, enviada debe ser true o false")
        if esperado.get("enviada") is False and any(campo in esperado for campo in CAMPOS_RESPUESTA):
            raise ErrorEsperado(f"{ruta}: {nombre} no se envía, así que no puede esperar una respuesta")
    return fotos


def _texto(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _descripcion(respuesta: Respuesta) -> str:
    if respuesta.estado is None:
        return respuesta.falla or "sin respuesta"
    codigo = (respuesta.cuerpo or {}).get("codigo")
    return f"HTTP {respuesta.estado}" + (f" {codigo}" if codigo else "")


def diferencias(esperado: dict[str, Any], obtenido: Obtenido) -> list[str]:
    """Lo que no coincide entre lo esperado de una foto y lo que pasó; vacío si todo coincide."""
    if "enviada" in esperado and esperado["enviada"] != obtenido.enviada:
        if obtenido.enviada:
            return ["se envió y se esperaba que no"]
        return [f"se esperaba que se enviara y no se envió ({obtenido.nota})"]

    campos = [campo for campo in CAMPOS_RESPUESTA if campo in esperado]
    if not campos:
        return []
    if not obtenido.enviada or obtenido.respuesta is None:
        return [f"no se envió ({obtenido.nota})"]

    respuesta = obtenido.respuesta
    if respuesta.estado != 200 or respuesta.cuerpo is None:
        return [f"se esperaba una respuesta 200 y llegó {_descripcion(respuesta)}"]

    lista = []
    for campo in campos:
        valor = respuesta.cuerpo.get(campo)
        if campo == "persona":
            valor = nombre_de(valor)
        if valor != esperado[campo]:
            lista.append(f"{campo}: se esperaba {_texto(esperado[campo])} y llegó {_texto(valor)}")
    return lista


def resumir(
    esperado: dict[str, dict[str, Any]],
    obtenidos: dict[str, Obtenido],
    salida: Callable[[str], None] = print,
) -> int:
    """Muestra el resumen y devuelve cuántas fotos tienen diferencias."""
    con_diferencias: list[tuple[str, list[str]]] = []
    for nombre, lo_esperado in esperado.items():
        if nombre not in obtenidos:
            con_diferencias.append((nombre, [f"está en {ARCHIVO_ESPERADO} pero no en la carpeta"]))
            continue
        lista = diferencias(lo_esperado, obtenidos[nombre])
        if lista:
            con_diferencias.append((nombre, lista))

    salida(
        f"Resumen: {contar(len(obtenidos), 'foto', 'fotos')}, {len(esperado)} con respuesta esperada, "
        f"{len(con_diferencias)} con diferencias."
    )
    for nombre, lista in con_diferencias:
        for diferencia in lista:
            salida(f"  {nombre}: {diferencia}")
    return len(con_diferencias)
