"""
Nombre: consentimiento.py
Descripción: Texto vigente del consentimiento, leído de specs/consentimiento.md (RF-02 · C3, D-07).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import re
from functools import lru_cache
from pathlib import Path

from accesia.esquemas import TextoConsentimiento

ARCHIVO = Path("specs") / "consentimiento.md"


def ruta_del_texto() -> Path:
    """Busca specs/consentimiento.md subiendo desde esta carpeta: sirve en el repositorio y en la imagen."""
    for carpeta in Path(__file__).resolve().parents:
        candidato = carpeta / ARCHIVO
        if candidato.is_file():
            return candidato
    raise FileNotFoundError(f"No encuentro {ARCHIVO.as_posix()} en ninguna carpeta superior.")


def extraer_texto(markdown: str) -> TextoConsentimiento:
    """El texto es el bloque entre las dos líneas «---» y la versión sale del título, como en el simulacro de la web."""
    lineas = markdown.splitlines()
    separadores = [indice for indice, linea in enumerate(lineas) if linea.strip() == "---"]
    if len(separadores) < 2:
        raise ValueError("consentimiento.md no tiene el texto entre dos líneas ---.")
    version = re.search(r"versión del texto (\d+(?:\.\d+)*)", markdown)
    if version is None:
        raise ValueError("consentimiento.md no dice la versión del texto en su título.")
    inicio, fin = separadores[0], separadores[1]
    return TextoConsentimiento(version=version.group(1), texto="\n".join(lineas[inicio + 1 : fin]).strip())


@lru_cache
def texto_vigente() -> TextoConsentimiento:
    return extraer_texto(ruta_del_texto().read_text(encoding="utf-8"))
