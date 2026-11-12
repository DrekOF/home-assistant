"""
Nombre: consola.py
Descripción: Cómo se muestra cada respuesta del servidor: una línea en la consola y un mensaje corto para la ventana de la webcam.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import sys
import unicodedata
from typing import Any

from simulador.envio import Respuesta


def nombre_de(persona: Any) -> str | None:
    return persona.get("nombre") if isinstance(persona, dict) else None


def numero(valor: float) -> str:
    """Con coma decimal, como en las specs: 0,710 o 2,5."""
    return f"{valor:g}".replace(".", ",")


def contar(cantidad: int, singular: str, plural: str) -> str:
    """«1 foto», «3 fotos»."""
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _similitud(valor: Any) -> str:
    return f"{valor:.3f}".replace(".", ",") if isinstance(valor, int | float) else "—"


def linea_respuesta(respuesta: Respuesta, espera: float) -> str:
    """Resultado, motivo, persona, similitud, repetido y, en modo inscribir, «Muestra 3 de 5»; al final, la espera."""
    if respuesta.estado is None:
        return f"{respuesta.falla} (espera {numero(espera)} s)"

    cuerpo = respuesta.cuerpo or {}
    if respuesta.estado == 200 and respuesta.cuerpo is not None:
        partes = [
            str(cuerpo.get("resultado") or "sin resultado"),
            f"motivo: {cuerpo.get('motivo') or '—'}",
            f"persona: {nombre_de(cuerpo.get('persona')) or '—'}",
            f"similitud: {_similitud(cuerpo.get('similitud'))}",
            f"repetido: {'sí' if cuerpo.get('repetido') else 'no'}",
        ]
        inscripcion = cuerpo.get("inscripcion")
        if cuerpo.get("modo") == "inscribir" and isinstance(inscripcion, dict):
            partes.append(f"Muestra {inscripcion.get('muestras')} de {inscripcion.get('requeridas')}")
        return " · ".join(partes) + f" (espera {numero(espera)} s)"

    texto = f"HTTP {respuesta.estado} {cuerpo.get('codigo') or 'sin código'}"
    if cuerpo.get("detalle"):
        texto += f": {cuerpo['detalle']}"
    return f"{texto} (espera {numero(espera)} s)"


def mensaje_corto(respuesta: Respuesta) -> str:
    """El último mensaje del servidor, para la ventana."""
    if respuesta.estado is None:
        return respuesta.falla or "sin respuesta"
    cuerpo = respuesta.cuerpo or {}
    if respuesta.estado == 200 and respuesta.cuerpo is not None:
        return f"{cuerpo.get('resultado')}: {cuerpo.get('mensaje') or ''}".rstrip(": ")
    return f"Error {respuesta.estado} {cuerpo.get('codigo') or ''}".rstrip()


def sin_tildes(texto: str) -> str:
    """cv2.putText solo dibuja ASCII: «Gómez» queda «Gomez» en la ventana (la consola sí lleva tildes)."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def preparar_salida() -> None:
    """Si la salida va a un archivo con otra codificación, un carácter raro se reemplaza.

    Así una tilde nunca corta el programa.
    """
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(errors="replace")
