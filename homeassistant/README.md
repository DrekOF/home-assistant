<!--
Nombre: README.md
Descripción: Configuración de Home Assistant de AccesIA (frente C).
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.1
-->

# Home Assistant · frente C

`config/` se monta como `/config` del contenedor de Home Assistant.

| Qué | Dónde |
| --- | --- |
| Configuración general (zona horaria `America/Bogota`, idioma español) | `config/configuration.yaml` |
| Automatizaciones: abrir la puerta y avisar desconocidos | `config/automatizaciones_accesia.yaml`, copiadas de `specs/contratos/mqtt.md` e incluidas desde `configuration.yaml`. `config/automations.yaml` queda para las que se creen en la interfaz |
| Panel «Portería» | `config/`, en YAML |
| Integraciones MQTT, Ollama y MCP | Se configuran desde la interfaz (`specs/contratos/mcp-agente.md`) y quedan en `.storage`, que Git ignora |

- Las entidades llegan solas por MQTT con descubrimiento: no se escriben a mano.
- El agente solo tiene las herramientas de AccesIA; «Control de dispositivos» queda apagado (D-15).
- La copia de seguridad para el kit se crea el Día 4.
- Se configura el Día 3 (`specs/plan.md`).
