"""
Nombre: ${up_revision}_${slug | n}.py
Descripción: ${message}
Fecha de creación: ${create_date.strftime("%Y-%m-%d")}
Actualización: ${create_date.strftime("%Y-%m-%d")}
Autor: Equipo AccesIA
Versión: 1.0
"""

from alembic import op
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
