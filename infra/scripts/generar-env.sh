#!/usr/bin/env bash
# Nombre: generar-env.sh
# Descripción: Crea infra/.env desde infra/.env.example con claves aleatorias, solo si todavía no existe (Linux y Raspberry).
# Fecha de creación: 2026-11-11
# Actualización: 2026-11-11
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio: ./infra/scripts/generar-env.sh

set -euo pipefail

infra="$(cd "$(dirname "$0")/.." && pwd)"
ejemplo="$infra/.env.example"
destino="$infra/.env"

if [ -e "$destino" ]; then
  echo "infra/.env ya existe; no lo cambio."
  exit 0
fi

# Claves que se llenan solas. SESION_SECRETO lleva 64 caracteres; las demás, 32.
claves=" POSTGRES_PASSWORD AGENTE_DB_PASSWORD SESION_SECRETO ADMIN_CLAVE_INICIAL MQTT_SERVIDOR_CLAVE MQTT_HA_CLAVE MQTT_CAMARA_CLAVE "

nueva_clave() {
  od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'
}

umask 077
temporal="$(mktemp)"
while IFS= read -r linea || [ -n "$linea" ]; do
  linea="${linea%$'\r'}"
  if [[ "$linea" =~ ^([A-Z_]+)=$ ]] && [[ "$claves" == *" ${BASH_REMATCH[1]} "* ]]; then
    nombre="${BASH_REMATCH[1]}"
    bytes=16
    if [ "$nombre" = "SESION_SECRETO" ]; then bytes=32; fi
    printf '%s=%s\n' "$nombre" "$(nueva_clave "$bytes")"
  else
    printf '%s\n' "$linea"
  fi
done < "$ejemplo" > "$temporal"
mv "$temporal" "$destino"
echo "Listo: se creó infra/.env con claves nuevas. No lo subas a Git."
