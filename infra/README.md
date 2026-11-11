<!--
Nombre: README.md
Descripción: Docker Compose, variables de entorno, Mosquitto y scripts del kit de AccesIA (frentes B y C).
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Infraestructura · frentes B y C

| Qué | Archivo |
| --- | --- |
| Servicios (`specs/arquitectura.md`) | `compose.yaml` |
| Escenario 2: Home Assistant OS en la Raspberry y el resto en el portátil | `compose.escenario2.yaml` (Día 4) |
| Variables (Git ignora `.env`) | `.env.example` → copiar a `.env` |
| Broker MQTT | `mosquitto/mosquitto.conf`, `mosquitto/acl`, `mosquitto/claves/` (ignorada) |
| Scripts | `scripts/`: generar `.env`, claves de MQTT y, el Día 4, `instalar.sh` y `verificar.sh` del kit |

Compose lee `infra/.env` solo, porque está en la misma carpeta que `compose.yaml`.

## Comandos

Se completan con la tarea B del Día 1.
