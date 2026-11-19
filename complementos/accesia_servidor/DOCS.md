<!--
Nombre: DOCS.md
Descripción: Documentación del complemento accesia_servidor, en la pestaña Documentación de Home Assistant OS.
Fecha de creación: 2026-11-18
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.0
-->

# AccesIA · servidor

La API, la web, MQTT y el servidor MCP de AccesIA, en la Pi (D-22).

| Qué | Dónde |
| --- | --- |
| Web de administración y API | `http://<IP de la Pi>:8000/`, sin Ingress |
| MCP del agente, solo para Home Assistant | `http://local-accesia-servidor:8001/mcp`, sin publicar (D-16) |
| Base | `local-accesia-base:5432`, con el usuario `accesia` |
| Broker | `core-mosquitto:1883`, con el usuario `servidor` |

## Antes de arrancarlo

1. Arranca **AccesIA · base de datos** con su clave.
2. En el complemento **Mosquitto**, pon en `logins` los usuarios `servidor` y `camara` con sus claves, y la ACL de `specs/contratos/mqtt.md` en `/share/mosquitto/` (`specs/arquitectura.md`, «Complementos de Home Assistant OS»).
3. Llena las opciones de este complemento. Las claves son las de `infra/.env` del portátil, que crea `generar-env.ps1`.

## Opciones

| Opción | Variable de `infra/.env` | Para qué |
| --- | --- | --- |
| `clave_base` | `POSTGRES_PASSWORD` | La misma de AccesIA · base de datos |
| `clave_agente` | `AGENTE_DB_PASSWORD` | El usuario de solo lectura del MCP (D-15) |
| `clave_mqtt_servidor` | `MQTT_SERVIDOR_CLAVE` | El usuario `servidor` de Mosquitto |
| `sesion_secreto` | `SESION_SECRETO` | Firma la cookie de la web |
| `admin_correo` y `admin_clave_inicial` | `ADMIN_CORREO` y `ADMIN_CLAVE_INICIAL` | El primer administrador |
| `umbral_similitud` … `nitidez_min` | Las de las reglas | R1, R4, R6, R7 y R9 (D-14). Se cambian aquí y se reinicia el complemento |

Las claves se escriben ocultas y solo root puede leerlas dentro del contenedor.

## Comandos

- **Cámaras:** se crean en la web, en la pantalla Cámaras, que muestra el token una sola vez (RF-10 · C1).
- **Semilla del agente:** con la acción `hassio.app_stdin` de Home Assistant (en Herramientas para desarrolladores → Acciones), para este complemento, con uno de estos textos:
  - `semilla agente`
  - `semilla agente --con-datos-reales`
  - `semilla agente --borrar`

  El resultado sale en el registro del complemento.

## Cómo corre

- El servidor corre con el usuario `accesia`.
- El MCP corre con el usuario `agente`, sin las claves del dueño de la base: solo tiene la del usuario `agente`, que solo lee las vistas del agente (D-15).
- Si alguno de los dos termina, el complemento se detiene. Con el Watchdog encendido, Supervisor lo vuelve a arrancar.
