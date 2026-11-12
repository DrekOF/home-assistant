"""
Nombre: db.py
Descripción: Conexión del servidor de AccesIA con PostgreSQL 18 + pgvector: motor, una transacción por petición y errores de la base.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from accesia.config import configuracion

# SQLSTATE de PostgreSQL que la API traduce a códigos del contrato.
VIOLACION_UNICA = "23505"
VIOLACION_LLAVE_FORANEA = "23503"
VIOLACION_RESTRICT = "23001"  # borrar un horario en uso (specs/contratos/README.md, versión 1.2)


@lru_cache
def motor() -> Engine:
    """Motor de SQLAlchemy del proceso, creado la primera vez que se usa."""
    return create_engine(
        configuracion().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def base_disponible() -> bool:
    """True si la base responde a una consulta simple."""
    try:
        with motor().connect() as conexion:
            conexion.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


@contextmanager
def transaccion() -> Iterator[Connection]:
    """Una transacción: se confirma al salir sin errores y se deshace si algo falla."""
    with motor().begin() as conexion:
        yield conexion


def obtener_conexion() -> Iterator[Connection]:
    """Dependencia de FastAPI: una transacción por petición. Las pruebas la reemplazan por la suya."""
    with transaccion() as conexion:
        yield conexion


# scope="function": la transacción se confirma al terminar la función de la ruta, antes de enviar la
# respuesta. Así, quien recibe un 201 ya puede leer lo que se guardó.
Conexion = Annotated[Connection, Depends(obtener_conexion, scope="function")]


def violacion(error: IntegrityError) -> str | None:
    """SQLSTATE de la restricción que falló (por ejemplo, 23505 para un valor único repetido)."""
    return getattr(error.orig, "sqlstate", None)
