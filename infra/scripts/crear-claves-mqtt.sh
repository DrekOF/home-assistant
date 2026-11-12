#!/usr/bin/env bash
# Nombre: crear-claves-mqtt.sh
# Descripción: Genera infra/mosquitto/claves/passwd con los usuarios de MQTT, usando mosquitto_passwd dentro del contenedor (Linux y Raspberry).
# Fecha de creación: 2026-11-11
# Actualización: 2026-11-11
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio y después de generar-env: ./infra/scripts/crear-claves-mqtt.sh

set -euo pipefail
# En Git Bash de Windows, evita que las rutas del contenedor se conviertan en rutas de Windows.
export MSYS_NO_PATHCONV=1

infra="$(cd "$(dirname "$0")/.." && pwd)"
archivo_env="$infra/.env"
if [ ! -e "$archivo_env" ]; then
  echo "Falta infra/.env: corre primero ./infra/scripts/generar-env.sh." >&2
  exit 1
fi

valor() {
  sed -n "s/^$1=//p" "$archivo_env" | tr -d '\r' | head -n 1
}

servidor="$(valor MQTT_SERVIDOR_CLAVE)"
homeassistant="$(valor MQTT_HA_CLAVE)"
camara="$(valor MQTT_CAMARA_CLAVE)"
for par in "MQTT_SERVIDOR_CLAVE:$servidor" "MQTT_HA_CLAVE:$homeassistant" "MQTT_CAMARA_CLAVE:$camara"; do
  if [ -z "${par#*:}" ]; then
    echo "Falta ${par%%:*} en infra/.env." >&2
    exit 1
  fi
done

mkdir -p "$infra/mosquitto/claves"

archivo=/mosquitto/config/claves/passwd
# mosquitto_passwd -c no sobrescribe un archivo existente: se borra antes para poder correr el script otra vez.
guion="rm -f $archivo && \
mosquitto_passwd -b -c $archivo servidor \"\$1\" && \
mosquitto_passwd -b $archivo homeassistant \"\$2\" && \
mosquitto_passwd -b $archivo camara \"\$3\" && \
{ chown mosquitto:mosquitto $archivo && chmod 0700 $archivo || true; }"

# Ruta relativa al compose.yaml: con MSYS_NO_PATHCONV, Git Bash no convertiría una ruta absoluta.
cd "$infra"
docker compose -f compose.yaml run --rm --no-deps --entrypoint sh mosquitto -c "$guion" claves \
  "$servidor" "$homeassistant" "$camara"

echo "Listo: infra/mosquitto/claves/passwd tiene los usuarios servidor, homeassistant y camara."
