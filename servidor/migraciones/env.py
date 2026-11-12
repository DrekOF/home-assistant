"""
Nombre: env.py
Descripción: Entorno de Alembic del servidor de AccesIA: conecta con la base de DATABASE_URL y corre las migraciones.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from accesia.config import Configuracion

config = context.config

if config.config_file_name is not None and config.attributes.get("configurar_registro", True):
    fileConfig(config.config_file_name)


def url_de_la_base() -> str:
    """Las pruebas pasan la URL en config.attributes; el contenedor la toma de DATABASE_URL."""
    return config.attributes.get("url") or Configuracion().database_url


def migrar_en_linea() -> None:
    motor = create_engine(url_de_la_base(), poolclass=NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=None, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
    motor.dispose()


if context.is_offline_mode():
    raise RuntimeError("Las migraciones de AccesIA solo corren conectadas a la base.")

migrar_en_linea()
