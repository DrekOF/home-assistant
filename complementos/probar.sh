#!/usr/bin/env bash
# Nombre: probar.sh
# Descripción: Arranca los dos complementos de amd64 como los arranca Home Assistant OS, sin la Pi, y revisa la salud, la web, el MCP, sus usuarios y las opciones (B4, D-22).
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz, con las imágenes ya construidas (complementos/README.md):
#   bash complementos/probar.sh
# Usa una red y volúmenes de Docker propios, con los nombres de la red interna de Supervisor, y los borra al terminar.
# Funciona en Linux (la CI) y en Git Bash con Docker Desktop. Sale con código 1 si algo falla.
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash no cambia las rutas de los contenedores

RED=accesia-prueba-complementos
BASE_IMAGEN=${BASE_IMAGEN:-local/accesia-base}
SERVIDOR_IMAGEN=${SERVIDOR_IMAGEN:-local/accesia-servidor}
PUERTO=${PUERTO:-18000}
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

limpiar() {
    docker rm -f prueba-servidor prueba-base prueba-mosquitto >/dev/null 2>&1 || true
    docker volume rm -f prueba-base-datos prueba-servidor-datos prueba-mosquitto-config >/dev/null 2>&1 || true
    docker network rm "$RED" >/dev/null 2>&1 || true
}
fallar() {
    echo "FALLA: $1" >&2
    for c in prueba-servidor prueba-base prueba-mosquitto; do
        echo "--- registro de $c ---" >&2
        docker logs --tail 40 "$c" >&2 2>&1 || true
    done
    exit 1
}
escribir() {  # escribir <volumen> <ruta en el volumen> < contenido
    docker run --rm -i -v "$1:/destino" --entrypoint sh "$BASE_IMAGEN" -c "cat > /destino/$2"
}
trap limpiar EXIT
limpiar

docker network create "$RED" >/dev/null
docker volume create prueba-base-datos >/dev/null
docker volume create prueba-servidor-datos >/dev/null
docker volume create prueba-mosquitto-config >/dev/null

# Mosquitto como core-mosquitto, con el mosquitto.conf y la ACL del repositorio y el usuario servidor.
escribir prueba-mosquitto-config mosquitto.conf < "$RAIZ/infra/mosquitto/mosquitto.conf"
escribir prueba-mosquitto-config acl < "$RAIZ/infra/mosquitto/acl"
docker run --rm -v prueba-mosquitto-config:/mosquitto/config eclipse-mosquitto:2 sh -c \
    'mkdir -p /mosquitto/config/claves && mosquitto_passwd -b -c /mosquitto/config/claves/passwd servidor prueba-mqtt-1234 \
     && chown -R mosquitto:mosquitto /mosquitto/config && chmod 0700 /mosquitto/config/claves/passwd'
docker run -d --name prueba-mosquitto --network "$RED" --network-alias core-mosquitto \
    -v prueba-mosquitto-config:/mosquitto/config eclipse-mosquitto:2 >/dev/null

# Las opciones de prueba, como las escribe Supervisor en /data/options.json.
echo '{"clave_base": "prueba-base-1234"}' | escribir prueba-base-datos options.json
cat <<'FIN' | escribir prueba-servidor-datos options.json
{
  "clave_base": "prueba-base-1234",
  "clave_agente": "prueba agente/1234@",
  "clave_mqtt_servidor": "prueba-mqtt-1234",
  "sesion_secreto": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "admin_correo": "admin@example.com",
  "admin_clave_inicial": "prueba-admin-1234",
  "umbral_similitud": 0.363,
  "ventana_repetido_s": 60,
  "alerta_desconocidos": 3,
  "alerta_ventana_s": 60,
  "inscripcion_muestras": 5,
  "inscripcion_vence_s": 120,
  "cara_min_px": 80,
  "nitidez_min": 60
}
FIN

inicio=$(date +%s)
docker run -d --name prueba-base --network "$RED" --network-alias local-accesia-base \
    -v prueba-base-datos:/data "$BASE_IMAGEN" >/dev/null
docker run -d --name prueba-servidor --network "$RED" --network-alias local-accesia-servidor \
    -v prueba-servidor-datos:/data -p "127.0.0.1:${PUERTO}:8000" "$SERVIDOR_IMAGEN" >/dev/null

echo "Esperando la salud del servidor..."
salud=""
for _ in $(seq 1 90); do
    salud=$(curl -fsS "http://127.0.0.1:${PUERTO}/api/v1/salud" 2>/dev/null || true)
    case "$salud" in *'"base":"ok"'*'"mqtt":"ok"'*) break ;; esac
    sleep 2
done
case "$salud" in *'"base":"ok"'*'"mqtt":"ok"'*) ;; *) fallar "la salud no llegó a base ok y mqtt ok: ${salud:-sin respuesta}" ;; esac
echo "Salud: $salud ($(( $(date +%s) - inicio )) s desde el arranque)"

curl -fsS "http://127.0.0.1:${PUERTO}/" | grep -q '<div id="raiz"' || fallar "la raíz no devuelve la web"
echo "La web sale en la raíz."

# Como el usuario agente, el del MCP: Docker no deja leer el entorno de un proceso de otro usuario, ni a root.
docker exec -i -u agente prueba-servidor python - <<'FIN' || fallar "el MCP no responde como dice mcp-agente.md"
import json, os, urllib.error, urllib.request

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

HERRAMIENTAS = sorted(["buscar_persona", "asistencia_del_dia", "llegadas_tarde", "accesos_de_persona",
                       "desconocidos_recientes", "fecha_y_hora_GetDateTime"])

INICIAR = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "prueba", "version": "1"}}}).encode()

def pedir(host):
    pedido = urllib.request.Request("http://127.0.0.1:8001/mcp", data=INICIAR, method="POST", headers={
        "Host": host, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(pedido, timeout=5) as respuesta:
            return respuesta.status, respuesta.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, ""

estado, cuerpo = pedir("local-accesia-servidor:8001")
assert estado == 200 and '"AccesIA"' in cuerpo, (estado, cuerpo[:200])
assert pedir("otra:8001")[0] == 421
print("MCP: initialize con el Host local-accesia-servidor:8001 y 421 con otro Host.")

async def listar():
    async with streamable_http_client("http://127.0.0.1:8001/mcp") as (leer, escribir), \
            ClientSession(leer, escribir) as sesion:
        await sesion.initialize()
        return sorted(herramienta.name for herramienta in (await sesion.list_tools()).tools)

nombres = anyio.run(listar)
assert nombres == HERRAMIENTAS, nombres
print(f"MCP: las {len(nombres)} herramientas de mcp-agente.md 1.5.")

usuarios = {}
for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        linea = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode()
        uid = next(l.split()[1] for l in open(f"/proc/{pid}/status") if l.startswith("Uid:"))
    except OSError:
        continue
    if "accesia mcp" in linea:
        usuarios["mcp"] = uid
    elif "uvicorn accesia.main:app" in linea:
        usuarios["servidor"] = uid
assert usuarios == {"mcp": "10002", "servidor": "10001"}, usuarios
entorno_mcp = next(open(f"/proc/{pid}/environ", "rb").read() for pid in filter(str.isdigit, os.listdir("/proc"))
                   if b"accesia mcp" in open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" "))
assert b"prueba-base-1234" not in entorno_mcp and b"SESION_SECRETO" not in entorno_mcp
print("El servidor corre como accesia (10001) y el MCP como agente (10002), sin las claves del dueño.")
assert oct(os.stat("/data/options.json").st_mode & 0o777) == "0o600"
try:
    open("/data/options.json").read()
except PermissionError:
    pass
else:
    raise AssertionError("El usuario agente pudo leer las opciones.")
print("Las opciones solo las lee root: el usuario agente no puede abrirlas.")
FIN

echo "Todo bien: los complementos arrancan como en Home Assistant OS."
