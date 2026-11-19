<!--
Nombre: README.md
Descripción: Los complementos de Home Assistant OS de AccesIA (D-22): qué hay, cómo se empaquetan, cómo se instalan en la Pi y cómo se prueban sin ella.
Fecha de creación: 2026-11-18
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.0
-->

# Complementos de Home Assistant OS

Con D-22, todo corre en la Raspberry Pi 5 como complementos de Home Assistant OS. Aquí están los dos nuestros. El Mosquitto oficial y el Ollama de SirUli se instalan desde la tienda (`specs/arquitectura.md`, «Complementos de Home Assistant OS»).

| Carpeta | Complemento | Qué hace |
| --- | --- | --- |
| `accesia_base/` | AccesIA · base de datos | PostgreSQL 18 con pgvector, con sus datos en `/data/postgres`. No publica puertos |
| `accesia_servidor/` | AccesIA · servidor | La API y la web en el 8000, MQTT y el MCP en el 8001, solo para la red interna |

Cada carpeta tiene su `config.yaml`, su `Dockerfile` con `FROM` explícito, su `run.sh`, `DOCS.md`, `README.md` y `translations/es.yaml`. `probar.sh` los arranca en el portátil como en Home Assistant OS.

## Empaquetar

Supervisor solo ve la carpeta del complemento, así que el del servidor necesita el código y lo demás adentro. Desde la raíz, en PowerShell, con Docker Desktop abierto:

```powershell
.\scripts\empaquetar-complementos.ps1
```

- Arma `kit\complementos\`, que Git ignora.
- `accesia_base` va tal cual.
- `accesia_servidor` lleva `servidor\` (sin pruebas ni `.venv`), `specs\contratos\base-de-datos.sql`, `specs\consentimiento.md`, la web compilada y los modelos de cara.
- La web y los modelos salen de las etapas `web` y `modelos` de `servidor\Dockerfile`: no hace falta Node ni uv, solo Docker.

## Instalar en la Pi

1. Instala el complemento **Samba share** y copia las dos carpetas de `kit\complementos\` a `\\<IP de la Pi>\addons\`.
2. En la tienda de complementos: ⋮ → «Buscar actualizaciones» → «Complementos locales». Instala **AccesIA · base de datos** y **AccesIA · servidor**. La Pi construye cada imagen; necesita internet una vez. Si la Pi solo está en clase, se usa el del celular (D-22).
3. **AccesIA · base de datos:** pon `clave_base` (la `POSTGRES_PASSWORD` de `infra\.env`) y arráncalo.
4. **Mosquitto:**
   - en `logins`, los usuarios `servidor` y `camara` con sus claves de `infra\.env`;
   - `customize` activo con la carpeta `mosquitto`;
   - en `/share/mosquitto/`, `acl.conf` con `acl_file /share/mosquitto/accesscontrollist`, y en `accesscontrollist`, la ACL de `infra\mosquitto\acl` (`mqtt.md` 1.4).
5. **AccesIA · servidor:** llena las opciones con las claves de `infra\.env`, enciende el Watchdog y arráncalo. En el registro debe decir que corrió la migración, y la web abre en `http://<IP de la Pi>:8000/`.
6. En Home Assistant, la integración Model Context Protocol con `http://local-accesia-servidor:8001/mcp` (`mcp-agente.md`).

Los comandos en la Pi:

- las cámaras, en la web, en la pantalla Cámaras;
- la semilla del agente, con la acción `hassio.app_stdin` y el texto `semilla agente` (`accesia_servidor/DOCS.md`).

## Probar sin la Pi

```bash
docker build --build-arg BUILD_ARCH=amd64 -t local/accesia-base kit/complementos/accesia_base
docker build --build-arg BUILD_ARCH=amd64 -t local/accesia-servidor kit/complementos/accesia_servidor
bash complementos/probar.sh
```

`probar.sh` los arranca como en Home Assistant OS, en una red de Docker propia:

- con los nombres `local-accesia-base`, `local-accesia-servidor` y `core-mosquitto`;
- con un `options.json` de prueba en `/data`.

Revisa:

- la salud, con la base y MQTT conectados;
- la web en la raíz;
- el `initialize` del MCP con el `Host` `local-accesia-servidor:8001`, y el 421 con otro `Host`;
- que el MCP corra con el usuario `agente` y que las opciones solo las lea root.

En la CI, `.github/workflows/complementos.yml` hace lo mismo en amd64 y construye los dos para arm64 con QEMU. En el portátil, el arm64 se prueba con `docker buildx build --platform linux/arm64`.
