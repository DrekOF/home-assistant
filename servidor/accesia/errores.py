"""
Nombre: errores.py
Descripción: Errores de la API de AccesIA con el esquema Error de specs/contratos/openapi.yaml (detalle y codigo).
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

import logging
from collections.abc import Mapping
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

registro = logging.getLogger(__name__)

# Los mismos códigos del enum de Error en openapi.yaml 1.3.
CodigoError = Literal[
    "sin_sesion",
    "credenciales_invalidas",
    "token_invalido",
    "dispositivo_inactivo",
    "no_encontrado",
    "metodo_no_permitido",
    "documento_duplicado",
    "codigo_duplicado",
    "nombre_duplicado",
    "consentimiento_vigente",
    "version_texto_invalida",
    "sin_consentimiento",
    "inscripcion_activa",
    "inscripcion_terminada",
    "horario_en_uso",
    "asistencia_duplicada",
    "imagen_grande",
    "tipo_no_soportado",
    "imagen_invalida",
    "demasiadas_peticiones",
    "validacion",
    "error_interno",
]


class Error(BaseModel):
    """Cuerpo de todos los errores de la API."""

    detalle: str
    codigo: CodigoError


class ErrorAccesIA(Exception):
    """Error de una regla o de un recurso, con su código HTTP y su código del contrato."""

    def __init__(self, estado: int, codigo: CodigoError, detalle: str) -> None:
        super().__init__(detalle)
        self.estado = estado
        self.codigo = codigo
        self.detalle = detalle


def respuesta_error(
    estado: int, codigo: CodigoError, detalle: str, cabeceras: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=estado, content=Error(detalle=detalle, codigo=codigo).model_dump(), headers=cabeceras
    )


def _campo(error: dict) -> str:
    """Nombre del campo que falló, sin la parte (body, query, path) que agrega FastAPI; vacío si es todo el cuerpo."""
    ubicacion = [str(parte) for parte in error.get("loc", ())]
    return ".".join(ubicacion[1:])


def explicar_validacion(errores: list[dict]) -> str:
    """Un detalle en español: los campos que fallaron y las frases de las reglas propias (ValueError)."""
    campos: set[str] = set()
    frases: dict[str, None] = {}  # un dict conserva el orden y no repite
    for error in errores:
        tipo = error.get("type")
        if tipo == "value_error":
            frases[str(error.get("msg", "")).removeprefix("Value error, ")] = None
        elif campo := _campo(error):
            campos.add(campo)
        elif tipo == "json_invalid":
            frases["El cuerpo no es un JSON válido."] = None
        else:
            frases["Revisa el cuerpo de la petición."] = None
    detalle = "Los datos no son válidos"
    if campos:
        detalle += ": revisa " + ", ".join(f"«{campo}»" for campo in sorted(campos))
    return " ".join([detalle + ".", *frases])


def registrar_manejadores(app: FastAPI) -> None:
    """Hace que todo error de la API responda con el esquema Error."""

    @app.exception_handler(ErrorAccesIA)
    async def error_accesia(_: Request, error: ErrorAccesIA) -> JSONResponse:
        return respuesta_error(error.estado, error.codigo, error.detalle)

    @app.exception_handler(RequestValidationError)
    async def error_de_validacion(_: Request, error: RequestValidationError) -> JSONResponse:
        return respuesta_error(422, "validacion", explicar_validacion(list(error.errors())))

    @app.exception_handler(StarletteHTTPException)
    async def error_http(_: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code == 404:
            return respuesta_error(404, "no_encontrado", "No existe.")
        if error.status_code == 405:
            # Contrato 1.3: la ruta existe pero no con ese método. Se conserva la cabecera Allow.
            return respuesta_error(405, "metodo_no_permitido", "Esa ruta no acepta ese método.", error.headers)
        return respuesta_error(error.status_code, "error_interno", str(error.detail), error.headers)

    @app.exception_handler(Exception)
    async def error_interno(_: Request, error: Exception) -> JSONResponse:
        registro.exception("Error no controlado en la API", exc_info=error)
        return respuesta_error(500, "error_interno", "Ocurrió un error interno. Intenta de nuevo.")
