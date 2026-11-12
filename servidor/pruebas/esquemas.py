"""
Nombre: esquemas.py
Descripción: Valida respuestas de la API contra los esquemas de specs/contratos/openapi.yaml en las pruebas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

OPENAPI = Path(__file__).resolve().parents[2] / "specs" / "contratos" / "openapi.yaml"


@lru_cache
def _componentes() -> dict:
    return yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))["components"]


def validar(esquema: str, datos: object) -> None:
    """Falla si los datos no cumplen components/schemas/<esquema> del contrato (OpenAPI 3.1 es JSON Schema 2020-12)."""
    raiz = {"$ref": f"#/components/schemas/{esquema}", "components": _componentes()}
    Draft202012Validator(raiz).validate(datos)
