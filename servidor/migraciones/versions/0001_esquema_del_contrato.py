"""
Nombre: 0001_esquema_del_contrato.py
Descripción: Migración inicial: ejecuta tal cual specs/contratos/base-de-datos.sql y crea el usuario agente (D-15).
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path

from alembic import op
from psycopg import sql

from accesia.config import Configuracion

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CONTRATO = Path("specs") / "contratos" / "base-de-datos.sql"


def ruta_del_contrato() -> Path:
    """Busca el SQL del contrato subiendo desde esta carpeta: sirve en el repositorio y en la imagen."""
    for carpeta in Path(__file__).resolve().parents:
        candidato = carpeta / CONTRATO
        if candidato.is_file():
            return candidato
    raise FileNotFoundError(f"No encuentro {CONTRATO.as_posix()} en ninguna carpeta superior.")


def upgrade() -> None:
    clave = Configuracion().agente_db_password
    if clave is None or not clave.get_secret_value():
        raise RuntimeError("Falta AGENTE_DB_PASSWORD: la migración crea el usuario agente con esa clave.")

    # El cursor de psycopg ejecuta el archivo completo en la misma transacción de Alembic, sin parámetros:
    # así el SQL va tal cual y SQLAlchemy no interpreta nada del texto.
    conexion = op.get_bind().connection.driver_connection
    with conexion.cursor() as cursor:
        cursor.execute(ruta_del_contrato().read_text(encoding="utf-8"))

        literal = sql.Literal(clave.get_secret_value())
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'agente'")
        if cursor.fetchone() is None:
            cursor.execute(sql.SQL("CREATE ROLE agente LOGIN PASSWORD {} IN ROLE accesia_agente").format(literal))
        else:
            # El rol es de todo el servidor de PostgreSQL: si ya existía, se deja con la clave de ahora.
            cursor.execute(sql.SQL("ALTER ROLE agente WITH LOGIN PASSWORD {}").format(literal))
            cursor.execute("GRANT accesia_agente TO agente")


def downgrade() -> None:
    raise NotImplementedError("La migración inicial no se deshace: se borra el volumen datos-postgres.")
