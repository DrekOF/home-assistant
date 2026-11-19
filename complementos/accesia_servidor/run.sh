#!/usr/bin/env bash
# Nombre: run.sh
# Descripción: Arranca el complemento accesia_servidor: lee las opciones, espera la base, corre la migración y levanta la API con la web en el 8000 y el MCP en el 8001, cada uno con su usuario. Si uno termina, sale para que Supervisor reinicie el complemento.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# - El servidor corre con el usuario accesia y las variables de arquitectura.md (Configuración), armadas desde
#   /data/options.json.
# - El MCP corre con el usuario agente y un entorno limpio: solo la DATABASE_URL del usuario agente de la base, la
#   zona horaria y su Host (D-15, mcp-agente.md). Las opciones quedan legibles solo para root.
# - Por la entrada estándar (acción hassio.app_stdin) acepta «semilla agente», con «--con-datos-reales» o
#   «--borrar». Las cámaras se crean en la web, que muestra el token una sola vez (RF-10 · C1).
set -euo pipefail

OPCIONES=/data/options.json
BASE=local-accesia-base
BROKER=core-mosquitto
HOST_MCP=local-accesia-servidor:8001

opcion() { jq -er --arg clave "$1" '.[$clave]' "$OPCIONES"; }
en_url() { jq -er --arg clave "$1" '.[$clave] | @uri' "$OPCIONES"; }
como() {
    local usuario="$1"
    shift
    setpriv --reuid="$usuario" --regid="$usuario" --init-groups -- "$@"
}

export ZONA_HORARIA=America/Bogota
export DATABASE_URL="postgresql+psycopg://accesia:$(en_url clave_base)@${BASE}:5432/accesia"
export MQTT_URL="mqtt://servidor:$(en_url clave_mqtt_servidor)@${BROKER}:1883"
AGENTE_DB_PASSWORD="$(opcion clave_agente)"
SESION_SECRETO="$(opcion sesion_secreto)"
ADMIN_CORREO="$(opcion admin_correo)"
ADMIN_CLAVE_INICIAL="$(opcion admin_clave_inicial)"
export AGENTE_DB_PASSWORD SESION_SECRETO ADMIN_CORREO ADMIN_CLAVE_INICIAL
for regla in umbral_similitud ventana_repetido_s alerta_desconocidos alerta_ventana_s inscripcion_muestras \
             inscripcion_vence_s cara_min_px nitidez_min; do
    export "${regla^^}=$(opcion "$regla")"
done
URL_AGENTE="postgresql+psycopg://agente:$(en_url clave_agente)@${BASE}:5432/accesia"
chmod 600 "$OPCIONES"

echo "AccesIA · servidor: esperando la base en ${BASE}:5432..."
base_lista=no
for _ in $(seq 1 90); do
    if como accesia python -c 'import os, psycopg; psycopg.connect(os.environ["DATABASE_URL"].replace("+psycopg", ""), connect_timeout=3).close()' 2>/dev/null; then
        base_lista=si
        break
    fi
    sleep 2
done
if [ "$base_lista" != si ]; then
    echo "La base no respondió en 3 minutos: revisa que AccesIA · base de datos esté arrancado y que clave_base sea la misma en los dos." >&2
    exit 1
fi

echo "Migración de la base..."
como accesia alembic upgrade head

echo "API y web en el 8000; MCP en el 8001, para Home Assistant en http://${HOST_MCP}/mcp."
como accesia uvicorn accesia.main:app --host 0.0.0.0 --port 8000 &
servidor=$!
env -i PATH="$PATH" HOME=/app PYTHONUNBUFFERED=1 ZONA_HORARIA="$ZONA_HORARIA" DATABASE_URL="$URL_AGENTE" \
    MCP_HOSTS_PERMITIDOS="$HOST_MCP" setpriv --reuid=agente --regid=agente --init-groups -- accesia mcp &
mcp=$!
trap 'kill -TERM "$servidor" "$mcp" 2>/dev/null || true' TERM INT

# Los comandos de la acción hassio.app_stdin. Un proceso en segundo plano no hereda la entrada estándar: va por el 3.
exec 3<&0
(
    while IFS= read -r linea <&3; do
        case "$linea" in
            "semilla agente" | "semilla agente --con-datos-reales" | "semilla agente --borrar")
                echo "Comando: accesia $linea"
                # shellcheck disable=SC2086  # el comando es uno de los tres de arriba, sin comillas a propósito
                como accesia accesia $linea || echo "El comando terminó con error."
                ;;
            "") ;;
            *) echo "Comando no permitido: «$linea». Se aceptan: semilla agente, semilla agente --con-datos-reales y semilla agente --borrar." ;;
        esac
    done
) &

codigo=0
wait -n "$servidor" "$mcp" || codigo=$?
echo "Un proceso del servidor terminó (código $codigo): el complemento se detiene para que Supervisor lo reinicie." >&2
kill -TERM "$servidor" "$mcp" 2>/dev/null || true
wait "$servidor" "$mcp" 2>/dev/null || true
exit $(( codigo == 0 ? 1 : codigo ))
