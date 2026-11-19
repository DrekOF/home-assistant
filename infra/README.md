<!--
Nombre: README.md
Descripción: Docker Compose, variables de entorno, Mosquitto y scripts del kit de AccesIA (frentes B y C).
Fecha de creación: 2026-11-11
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 1.10
-->

# Infraestructura · frentes B y C

| Qué | Archivo |
| --- | --- |
| Servicios (`specs/arquitectura.md`) | `compose.yaml`: `postgres`, `mosquitto`, `servidor` y `mcp` (el servidor MCP del agente, tarea B3 del Día 3). Ollama no va en Compose desde D-22: corre en la Pi, y en el portátil solo con `compose.ollama-portatil.yaml` (Día 4) y el visto bueno del profesor |
| Escenario 2, el plan B desde D-22: Home Assistant OS, Mosquitto y Ollama en la Raspberry, y la base, el servidor y el MCP en el portátil (D-23) | `compose.escenario2.yaml`, que publica `mcp`, y `compose.broker-pi.yaml`, que lleva el servidor al broker de la Pi; los dos con `compose.yaml` (ver «Plan B: escenario 2») |
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
| Abrir la web de administración, que sirve el servidor (no necesita Node) | `start http://localhost:8000` |
| Registrar una cámara y ver su token una sola vez | `docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador` |
| Registrar una cámara de respaldo, a la que el servidor le pide una foto por segundo (paso a paso en `servidor/README.md`, «Modo extraer») | `docker compose -f infra/compose.yaml exec servidor accesia crear-camara patio --nombre Patio --tipo respaldo --url-captura http://<IP de la cámara>/capture` |
| Ver los registros del servidor (una línea INFO por recorte, sin imágenes) | `docker compose -f infra/compose.yaml logs -f servidor` |
| Ver el registro del servidor MCP (dice qué encabezados `Host` acepta) | `docker compose -f infra/compose.yaml logs -f mcp` |
| Crear los datos de la evaluación del agente y revisar las preguntas 1 a 9 | `docker compose -f infra/compose.yaml exec servidor accesia semilla agente` |
| Borrar solo los datos de esa semilla | `docker compose -f infra/compose.yaml exec servidor accesia semilla agente --borrar` |
| Mirar el tráfico de MQTT (eventos, alertas, resumen y disponibilidad) | `docker compose -f infra/compose.yaml exec mosquitto mosquitto_sub -u servidor -P "<MQTT_SERVIDOR_CLAVE>" -t "accesia/#" -v` |
| Mirar el descubrimiento de Home Assistant (los config retenidos) | `docker compose -f infra/compose.yaml exec mosquitto mosquitto_sub -u servidor -P "<MQTT_SERVIDOR_CLAVE>" -t "homeassistant/#" -v` |
| Bajar todo y conservar los datos | `docker compose -f infra/compose.yaml down` |
| Bajar todo y borrar los datos (fin del semestre) | `docker compose -f infra/compose.yaml down -v` |

Al arrancar, el servidor crea el administrador de `ADMIN_CORREO` con `ADMIN_CLAVE_INICIAL` si todavía no existe; con esos dos datos se entra a la web. Sin `SESION_SECRETO`, el servidor no arranca.

La primera construcción de la imagen descarga de GitHub los modelos de cara (YuNet y SFace, unos 39 MB) y comprueba su SHA-256: hace falta internet. Después quedan en la caché de capas de Docker y no se vuelven a bajar mientras `servidor/accesia/modelos.py` no cambie. El servidor los carga al arrancar y lo dice en su registro (`Modelos de cara cargados`).

Desde B2 del Día 3, el servidor se conecta a MQTT al arrancar, sin esperar al broker: `/api/v1/salud` responde `"mqtt": "ok"` y `"estado": "ok"` con la base y el broker bien, y `"mqtt": "sin_conexion"` y `"estado": "degradado"` mientras no está conectado. En `docker compose -f infra/compose.yaml logs servidor` se ve `MQTT: conectado a mosquitto:1883 como servidor.` Qué publica y cuándo está en `servidor/README.md` (MQTT).

## Servidor MCP del agente

El servicio `mcp` corre `accesia mcp` con la misma imagen del servidor (`servidor/README.md`, Servidor MCP del agente).

- No recibe `infra/.env`. Compose le arma `DATABASE_URL` con el usuario `agente` y `AGENTE_DB_PASSWORD`, así que nunca tiene la clave del dueño de la base (D-15).
- En `compose.yaml` no se publica fuera de la red de Docker (D-16). Dentro de ella, su dirección es `http://mcp:8001/mcp`.
- Acepta los encabezados `Host` `mcp:8001`, `localhost:8001`, `127.0.0.1:8001` y los de `MCP_HOSTS_PERMITIDOS`. Si `infra/.env` no trae esa variable, Compose usa `192.168.137.1:8001`.

**En el escenario 2,** Home Assistant OS llama al servidor MCP en `http://192.168.137.1:8001/mcp`, y `compose.escenario2.yaml` publica el 8001 (ver «Plan B: escenario 2»). Si el portátil no queda en `192.168.137.1`, su IP va en `MCP_HOSTS_PERMITIDOS` (por ejemplo, `MCP_HOSTS_PERMITIDOS=192.168.137.5:8001`) y se vuelve a crear el servicio `mcp`.

## Semilla del agente para la evaluación

`accesia semilla agente` crea los datos de las 10 preguntas de `specs/contratos/mcp-agente.md` con fechas relativas a hoy, y revisa las preguntas 1 a 9 con las herramientas.

- **Con los datos del Hito 1 en la base**, no escribe nada sin `--con-datos-reales`, y nunca toca lo que no creó.
- **Para medir en el portátil:**
  1. Justo antes de medir:

     ```powershell
     docker compose -f infra/compose.yaml exec servidor accesia semilla agente --con-datos-reales
     ```

  2. Medir, comparando cada respuesta con la que muestra la revisión.
  3. Al terminar:

     ```powershell
     docker compose -f infra/compose.yaml exec servidor accesia semilla agente --borrar
     ```

- Para medir otro día, se vuelve a correr: reemplaza lo suyo con las fechas de ese día.

## Plan B: escenario 2

Desde D-22, la demo corre en la Pi. Si los complementos no se pueden instalar, o la Pi no alcanza para la base y el servidor, se usa el escenario 2 (D-23): Home Assistant OS, su Mosquitto y Ollama siguen en la Pi, y la base, el servidor y el MCP corren en el portátil (`specs/arquitectura.md`, «Red y despliegue»).

- **`compose.escenario2.yaml`** publica `mcp` en el 8001 de la red del portátil, para que Home Assistant OS llegue al servidor MCP.
  - Es una excepción a D-16 y D-19, que vale solo en el hotspot o en otra red propia.
  - `compose.yaml` no tiene el servicio `homeassistant`, así que no hay nada que quitar.
- **`compose.broker-pi.yaml`** (D-23) conecta el servidor al Mosquitto de la Pi con el usuario `servidor`, y el Mosquitto del Compose no arranca. La IP sale de `IP_DE_LA_PI`, por defecto `192.168.137.250`. Home Assistant y la placa no se tocan.
- **Firewall:** antes de usarlo, una persona del equipo abre el firewall solo para la red del hotspot. Los cambios del firewall no los hace Claude Code:

  ```powershell
  New-NetFirewallRule -DisplayName "AccesIA plan B" -Direction Inbound -Protocol TCP -LocalPort 8001 -RemoteAddress 192.168.137.0/24 -Action Allow
  ```

  Con eso entra el 8001 (`mcp`). El 1883 se suma solo si el broker vuelve al portátil, el 8000 cuando la placa envíe recortes, y el 11434 solo si Ollama pasa al portátil, con el visto bueno del profesor.

| Para qué | Comando |
| --- | --- |
| Revisar la configuración sin levantar nada | `docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml -f infra/compose.broker-pi.yaml config --services` |
| Bajar el Compose de siempre, que trae su Mosquitto (conserva los datos) | `docker compose -f infra/compose.yaml down` |
| Levantar el plan B, con las imágenes ya construidas | `docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml -f infra/compose.broker-pi.yaml up -d` |
| Si la Pi quedó en otra IP, antes del `up` (o en `IP_DE_LA_PI` de `infra/.env`) | `$env:IP_DE_LA_PI = "<IP de la Pi>"` |
| Volver al Compose de siempre, con su Mosquitto y sin publicar el 8001 | `docker compose -f infra/compose.yaml up -d` |
| Quitar la regla del firewall | `Remove-NetFirewallRule -DisplayName "AccesIA plan B"` |

- **Si la Pi no tiene Mosquitto** (por ejemplo, porque no hubo internet para instalarlo), el broker vuelve al portátil, como antes de D-23:
  - se levanta sin `compose.broker-pi.yaml`: `docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml up -d`;
  - la regla del firewall suma el 1883: `Set-NetFirewallRule -DisplayName "AccesIA plan B" -LocalPort 1883,8001`;
  - en Home Assistant OS, la integración MQTT va a `192.168.137.1:1883` con el usuario `homeassistant` y su clave de `infra/.env`, y la placa se reconfigura por consola hacia `192.168.137.1`.

  Los pasos están en `docs/guia-dia-de-clase.md` (paso 7).
- **`MCP_HOSTS_PERMITIDOS`** de `infra/.env` debe tener la IP del portátil en el hotspot: `192.168.137.1:8001` por defecto.
- **Probado** el 2026-11-19 en el portátil, con un Mosquitto aparte que hacía de broker de la Pi: el servidor se conecta a él, la salud da `"mqtt":"ok"`, el MCP responde en el 8001 y el Mosquitto del Compose no arranca (bitácora, D-23). Falta la prueba con la Pi, en clase (C2, paso 5).

## Puertos reservados por Windows

Hyper-V y WSL reservan rangos de puertos al azar y pueden tomar el de PostgreSQL (`POSTGRES_PORT`, 5434 por defecto), el 8000 o el 1883. Para ver los rangos reservados:

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

Si `POSTGRES_PORT` cae dentro de un rango, cámbialo en `infra/.env` por uno libre (nunca el 5432) y vuelve a correr `docker compose -f infra/compose.yaml up -d`.

## Salud de Mosquitto

El healthcheck de `mosquitto` entra al broker con el usuario `servidor` y el client id `salud-broker`, y cada revisión deja tres líneas en su registro. Por eso revisa cada 2 s mientras arranca y después cada 5 min: queda sano igual de rápido y no tapa las conexiones de la placa, del servidor y de Home Assistant. Antes revisaba cada 10 s (18 líneas por minuto, lo que encontró el Hito 1). `servidor` espera a que `mosquitto` arranque, no a que esté sano.

## ACL de MQTT

`mosquitto/acl` es la ACL de `mqtt.md` 1.4, la misma del portátil y de la Pi (D-22). `homeassistant` y `addons` leen y escriben en todos los temas, porque Home Assistant lo espera del Mosquitto oficial. Si el broker del Compose ya corría, reinícialo para que la lea: `docker compose -f infra/compose.yaml restart mosquitto`.

La prueba `contrato MQTT · acl` levanta Mosquitto con `mosquitto/mosquitto.conf` y `mosquitto/acl` y comprueba la ACL con paho-mqtt. También revisa que `mosquitto/acl` tenga las mismas reglas que `mqtt.md`. Se corre desde `servidor/` con `uv run pytest -k acl`.
