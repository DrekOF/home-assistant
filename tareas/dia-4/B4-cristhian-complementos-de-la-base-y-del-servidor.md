<!--
Nombre: B4-cristhian-complementos-de-la-base-y-del-servidor.md
Descripción: Tarea B4 del Día 4 del frente B: los complementos de Home Assistant OS de la base y del servidor (D-22), su empaquetado para el kit, su CI para arm64 y amd64, y la ACL de MQTT al día con mqtt.md 1.4.
Fecha de creación: 2026-11-13
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.1
-->

# Día 4 · Frente B · B4 · Complementos de la base y del servidor

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/complementos`
- Depende de:
  - D-22 en `main` (PR #20), con `mqtt.md` 1.4 y `mcp-agente.md` 1.4, y el contrato del agente 1.5 (PR #21);
  - B1 de hoy, ya en `main` (PR #19): la web compilada viaja dentro del servidor;
  - nada de A ni de C. No necesita la Pi: se prueba en la CI, en el portátil y en el devcontainer (`specs/arquitectura.md`, «Cómo se prueban sin la Pi»).
  - Es el camino crítico del Hito 2, de la evaluación de B3, de C2 del Día 3 (Assist con el MCP) y del kit (C1).
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/decisiones.md`: D-14, D-16 y D-22, con «Cómo se aplica D-22» y «Lo que cambia en las decisiones anteriores con D-22»;
  - de `specs/arquitectura.md`: «Complementos de Home Assistant OS (D-22)», con «Presupuesto de RAM» y «Cómo se prueban sin la Pi»;
  - `specs/contratos/mqtt.md` 1.4 (los usuarios y la ACL) y, de `specs/contratos/mcp-agente.md` 1.5, las herramientas y «Configuración en Home Assistant»;
  - de `specs/requisitos.md`: RF-11 · C2, RNF-04 y RNF-06 · C3;
  - `servidor/Dockerfile`, `infra/README.md` y, de `servidor/README.md`, La web, Servidor MCP del agente y Semilla del agente.

## Objetivo

La base y el servidor corren como complementos locales de Home Assistant OS (D-22):

- `accesia_base`: PostgreSQL 18 con pgvector, con sus datos en `/data/postgres`;
- `accesia_servidor`: la API, la web, MQTT y el MCP, con su configuración en las opciones del complemento (D-14).

Además:

- `scripts/empaquetar-complementos.ps1` arma `kit/complementos/`, listo para copiar a la Pi;
- un workflow nuevo, `complementos.yml`, construye los dos para arm64 y amd64 y arranca los de amd64 (D-11);
- `infra/mosquitto/acl` y su prueba quedan al día con `mqtt.md` 1.4.

## Antes de empezar

- Propón en el plan:
  - **Dónde viven las dos carpetas** en el repositorio, cada una con su `config.yaml`, su `Dockerfile` con `FROM` explícito y su `run.sh`, como dice `arquitectura.md`. También cómo quedan en la estructura de `CLAUDE.md`.
  - **Las opciones de cada complemento:**
    - qué variables de `infra/.env` pasan a opciones, con sus valores por defecto;
    - cuáles son claves y cómo se marcan como tales en la interfaz de Home Assistant.
  - **El `run.sh` del servidor:**
    - lee las opciones y corre la migración;
    - arranca Uvicorn en el 8000 y `accesia mcp` en el 8001, con `MCP_HOSTS_PERMITIDOS=local-accesia-servidor:8001`;
    - termina si uno de los dos falla, para que Supervisor lo reinicie.
  - **Los comandos en la Pi:** cómo se corren `accesia crear-camara` y `accesia semilla agente`, que en el portátil van con `docker compose exec`.
  - **El empaquetado:**
    - qué copia `empaquetar-complementos.ps1`: el código del servidor, el SQL del contrato, `consentimiento.md`, la web compilada y los modelos de cara;
    - de dónde sale la web compilada: `npm run build` o la etapa `web` del `Dockerfile` de B1;
    - cómo arma la CI lo mismo.
  - **`complementos.yml`:**
    - qué construye y qué arranca con un `options.json` de prueba;
    - qué revisa: `/api/v1/salud` y un `initialize` del MCP;
    - cuánto tarda arm64 con QEMU.
  - **La ACL:** qué cambia en `infra/mosquitto/acl` con `mqtt.md` 1.4 (`homeassistant` y `addons` con acceso total) y cómo queda la prueba `contrato MQTT · acl`.

## Hacer

1. Las dos carpetas, con lo que se acuerde.
2. `scripts/empaquetar-complementos.ps1`, que arma `kit/complementos/`.
3. `.github/workflows/complementos.yml`:
   - construye los dos complementos para arm64 y amd64;
   - en amd64, los arranca con un `options.json` de prueba y revisa la salud, la web en la raíz y el MCP.
4. `infra/mosquitto/acl` con `mqtt.md` 1.4, y la prueba `contrato MQTT · acl` al día.
5. En el portátil, los dos en arm64 con emulación (`docker run --platform linux/arm64`, con `/data` montada): que arrancan, y cuánto tardan.
6. Si alcanza, instalarlos en el devcontainer de Home Assistant y comprobar que Home Assistant llega al MCP en `http://local-accesia-servidor:8001/mcp`. Es el ensayo de C2 del Día 3: se coordina con C.
7. Documentación:
   - un README de los complementos, con la instalación paso a paso;
   - `infra/README.md`, `CLAUDE.md` (los comandos nuevos) y `specs/arquitectura.md`, si algo cambia;
   - el paso de la instalación en `docs/guia-dia-de-clase.md`;
   - la bitácora.

## No hacer

- No publiques el 8001 ni el 5432 en la red del hotspot: solo el 8000 (D-16).
- No pongas claves en el repositorio: van en las opciones de cada complemento, y los ejemplos llevan solo los nombres.
- No subas `kit/complementos/`, los modelos, la web compilada ni nada de `/data`.
- No cambies los contratos ni lo que hace el servidor: si algo no encaja, se propone en el PR.
- No toques `web/`, `firmware/` ni `simulador/`.

## Criterios de aceptación

- C1 (D-22) Los dos complementos arrancan con un `options.json` de prueba:
  - el servidor se conecta a la base y corre la migración;
  - `/api/v1/salud` responde y la web sale en la raíz;
  - el MCP responde un `initialize` con el `Host` `local-accesia-servidor:8001` y lista las herramientas de `mcp-agente.md` 1.5.
- C2 (D-11; RNF-04 · C1) `complementos.yml` en verde: construye los dos para arm64 y amd64 y arranca los de amd64.
- C3 (RF-11 · C2) `empaquetar-complementos.ps1` arma `kit/complementos/` con el código del servidor, el SQL del contrato, `consentimiento.md`, la web compilada y los modelos de cara.
- C4 `infra/mosquitto/acl` cumple `mqtt.md` 1.4, y la prueba `contrato MQTT · acl` está al día y en verde.
- C5 (RNF-06 · C3) Todos los workflows del PR en verde; el README de los complementos, la guía y la bitácora al día.

## Al terminar

- Resume:
  - dónde quedaron las carpetas y qué opciones tiene cada complemento;
  - cómo se instalan en la Pi y cómo se corren los comandos allí;
  - qué prueba `complementos.yml` y cuánto tarda;
  - el arranque en arm64 con emulación, con sus tiempos;
  - qué cambió en la ACL.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con todos los workflows del PR en verde.
- Cuando esté en `main`, avisa a C: C1 arma el kit con las carpetas, y C2 del Día 3 conecta Assist con el MCP.
- El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
