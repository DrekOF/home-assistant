#!/usr/bin/env bash
# Nombre: run.sh
# Descripción: Arranca el complemento accesia_base: lee la clave de las opciones y arranca PostgreSQL con sus datos en /data/postgres.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# La clave solo cuenta la primera vez, cuando PostgreSQL crea la base: cambiarla después en las opciones no cambia
# la de la base, como pasa con POSTGRES_PASSWORD en el Compose del portátil.
set -euo pipefail

OPCIONES=/data/options.json

export POSTGRES_USER=accesia
export POSTGRES_DB=accesia
POSTGRES_PASSWORD="$(jq -er '.clave_base' "$OPCIONES")"
export POSTGRES_PASSWORD
export PGDATA=/data/postgres

# Solo root lee las opciones.
chmod 600 "$OPCIONES"

echo "AccesIA · base de datos: PostgreSQL con sus datos en $PGDATA."
exec docker-entrypoint.sh postgres
