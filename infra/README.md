<!--
Nombre: README.md
Descripción: Docker Compose, variables de entorno, Mosquitto y scripts del kit de AccesIA (frentes B y C).
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.3
-->

# Infraestructura · frentes B y C

| Qué | Archivo |
| --- | --- |
| Servicios (`specs/arquitectura.md`) | `compose.yaml`: `postgres`, `mosquitto` y `servidor`; Home Assistant, Ollama y el MCP llegan el Día 3 |
| Escenario 2: Home Assistant OS en la Raspberry y el resto en el portátil | `compose.escenario2.yaml` (Día 4) |
| Variables (Git ignora `.env`) | `.env.example`; `scripts/generar-env` crea `.env` con claves nuevas |
| Broker MQTT | `mosquitto/mosquitto.conf`, `mosquitto/acl` y `mosquitto/claves/` (ignorada) |
| Scripts | `scripts/`: `generar-env` y `crear-claves-mqtt`, en `.ps1` (Windows) y `.sh` (Linux y Raspberry); el Día 4, `instalar.sh` y `verificar.sh` del kit |

Compose lee `infra/.env` solo, porque está en la misma carpeta que `compose.yaml`.

## Comandos

Desde la raíz del repositorio, en PowerShell.

Una sola vez:

| Para qué | Comando |
| --- | --- |
| Crear `infra/.env` con claves nuevas (no lo cambia si ya existe) | `.\infra\scripts\generar-env.ps1` |
| Crear las claves de MQTT de los usuarios `servidor`, `homeassistant` y `camara` | `.\infra\scripts\crear-claves-mqtt.ps1` |

Si Windows no deja correr scripts, usa `powershell -ExecutionPolicy Bypass -File .\infra\scripts\generar-env.ps1` (y lo mismo con el otro). En Linux o en la Raspberry, los mismos scripts terminan en `.sh`.

Cada día:

| Para qué | Comando |
| --- | --- |
| Construir y levantar todo | `docker compose -f infra/compose.yaml up -d --build` |
| Ver si están sanos | `docker compose -f infra/compose.yaml ps` |
| Probar el servidor | `curl.exe http://localhost:8000/api/v1/salud` |
| Registrar una cámara y ver su token una sola vez | `docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador` |
| Ver los registros del servidor (una línea INFO por recorte, sin imágenes) | `docker compose -f infra/compose.yaml logs -f servidor` |
| Mirar el tráfico de MQTT | `docker compose -f infra/compose.yaml exec mosquitto mosquitto_sub -u servidor -P "<MQTT_SERVIDOR_CLAVE>" -t "accesia/#" -v` |
| Bajar todo y conservar los datos | `docker compose -f infra/compose.yaml down` |
| Bajar todo y borrar los datos (fin del semestre) | `docker compose -f infra/compose.yaml down -v` |

Al arrancar, el servidor crea el administrador de `ADMIN_CORREO` con `ADMIN_CLAVE_INICIAL` si todavía no existe; con esos dos datos se entra a la web. Sin `SESION_SECRETO`, el servidor no arranca.

La primera construcción de la imagen descarga de GitHub los modelos de cara (YuNet y SFace, unos 39 MB) y comprueba su SHA-256: hace falta internet. Después quedan en la caché de capas de Docker y no se vuelven a bajar mientras `servidor/accesia/modelos.py` no cambie. El servidor los carga al arrancar y lo dice en su registro (`Modelos de cara cargados`).

Hasta el Día 3, `/api/v1/salud` responde `"estado": "degradado"` y `"mqtt": "sin_conexion"`: el servidor todavía no se conecta a MQTT.

## Puertos reservados por Windows

Hyper-V y WSL reservan rangos de puertos al azar y pueden tomar el de PostgreSQL (`POSTGRES_PORT`, 5434 por defecto), el 8000 o el 1883. Para ver los rangos reservados:

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

Si `POSTGRES_PORT` cae dentro de un rango, cámbialo en `infra/.env` por uno libre (nunca el 5432) y vuelve a correr `docker compose -f infra/compose.yaml up -d`.

## ACL de MQTT

La prueba `contrato MQTT · acl` levanta Mosquitto con `mosquitto/mosquitto.conf` y `mosquitto/acl` y comprueba la ACL con paho-mqtt. Se corre desde `servidor/` con `uv run pytest -k acl`.
