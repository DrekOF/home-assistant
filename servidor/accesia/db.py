"""
Nombre: db.py
Descripción: Conexión del servidor de AccesIA con PostgreSQL 18 + pgvector.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from accesia.config import configuracion


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
