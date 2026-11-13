<!--
Nombre: C1-jhon-kit-del-dia-de-clase.md
Descripción: Tarea C1 del Día 4 del frente C: el kit del día de clase (RF-11), con D-22. Las carpetas de los complementos, el modelo de Ollama para copiarlo a la Pi, la copia cifrada de Home Assistant OS, el binario del C6, las imágenes de los planes B y C, los scripts instalar y verificar en PowerShell y en .sh, y la guía del día de clase al día.
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.1
-->

# Día 4 · Frente C · C1 · El kit del día de clase

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/kit`
- Depende de:
  - B4 de hoy: las carpetas de los complementos y `scripts/empaquetar-complementos.ps1`;
  - C2 del Día 3: Mosquitto y Ollama en la Pi, la copia de seguridad de Home Assistant OS y `compose.escenario2.yaml` para el plan B;
  - A2 de hoy: el binario del C6 probado y sus pasos de flasheo;
  - A3 de hoy: la IP de la Pi en los valores de fábrica;
  - A1 de hoy: los valores calibrados;
  - B1 de hoy, ya en `main`: la web va dentro del servidor.
  - Los scripts y la guía pueden empezar antes, con lo que ya está en `main`.
  - La copia de Home Assistant OS y `verificar` contra la Pi necesitan la Pi: si solo está en clase, se hacen allá (00).
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/requisitos.md`: RF-11, RNF-03 · C3 y RNF-04;
  - de `specs/decisiones.md`: D-06, D-09, D-16, D-21 y D-22, con «Cómo se aplica D-22» y «Lo que cambia en las decisiones anteriores con D-22»;
  - de `specs/arquitectura.md`: «Complementos de Home Assistant OS (D-22)», con «Cómo se prueban sin la Pi», Servicios de Docker Compose y Red y despliegue;
  - `docs/guia-dia-de-clase.md`, `infra/README.md` y `homeassistant/README.md`.

## Objetivo

El kit del día de clase queda armado en el portátil y se usa sin internet, salvo para instalar los complementos en la Pi (RF-11 con D-22; RNF-04 · C3). Lleva:

- las carpetas de los complementos `accesia_base` y `accesia_servidor`, con los modelos de cara;
- los archivos del modelo de Ollama, para copiarlos a la Pi sin internet;
- la copia de seguridad cifrada de Home Assistant OS, sin inscripciones;
- el binario del C6 con esptool;
- para el plan B, las imágenes del portátil, y para el plan C, las imágenes arm64;
- los scripts `instalar` y `verificar`.

`verificar` revisa la Pi desde el portátil y queda en verde, y la guía del día de clase dice los pasos reales. El arranque desde cero con cronómetro es del ensayo del Día 5.

## Antes de empezar

- Propón en el plan:
  - **Qué scripts y en qué lenguaje.** RF-11 · C1 los nombra en PowerShell y en `.sh`:
    - en PowerShell para el portátil con Windows, como `generar-env` y `crear-claves-mqtt`;
    - en `.sh` para el escenario 1 en Raspberry Pi OS, que con D-22 es el plan C.
    - Con D-22, `verificar` revisa la Pi desde el portátil, e `instalar` queda para los planes B y C.
  - **Qué revisa `verificar` (RF-11 · C1):**
    - los complementos: la salud del servidor con `base` y `mqtt` en `ok`, y la web en `http://<IP de la Pi>:8000`;
    - MQTT: el descubrimiento retenido del servidor y de la placa;
    - las entidades en Home Assistant;
    - Ollama, con el modelo cargado;
    - la placa en línea (`en_linea` de la cámara).
    - El 8001 y el 11434 no se publican en la Pi (D-16): propón cómo revisa el MCP y Ollama sin publicarlos, por ejemplo a través de Home Assistant.
    - Propón también qué hace si algo falla: dice qué y dónde mirar.
    - Con el plan B, revisa el Compose del portátil, como antes.
  - **`compose.ollama-portatil.yaml`.** Con D-22, Ollama corre en la Pi, y pasa al portátil solo con el visto bueno del profesor (RNF-03 · C3). Propón si se hace ahora, para tenerlo listo, o solo si el profesor lo aprueba.
  - **Las versiones exactas de las imágenes del plan B**, pendientes desde el Día 1: `pgvector/pgvector`, `eclipse-mosquitto`, `ollama/ollama` y la del servidor, fijadas en `infra/compose.yaml` y en `compose.escenario2.yaml`. Las de los complementos las fija B4 en sus `Dockerfile`.
  - **Qué lleva `kit/` y cómo:**
    - `kit/complementos/`, que arma `empaquetar-complementos.ps1` de B4;
    - el modelo de Ollama, para copiarlo por Samba a `/share/ollama`;
    - la copia de Home Assistant OS, cifrada y sin inscripciones;
    - el binario del C6 y esptool;
    - las imágenes del plan B en `.tar`, y las arm64 del plan C;
    - un índice con el tamaño de cada cosa. `kit/` lo ignora Git.
- Las claves no van en el kit:
  - en el portátil, `infra/.env` se genera con `generar-env`;
  - en la Pi, las claves van en las opciones de cada complemento.

## Hacer

1. Las versiones fijas en los Compose del plan B, revisadas con `docker compose … config`.
2. El kit en `kit/`:
   - las carpetas de los complementos, con el script de B4;
   - el modelo de Ollama;
   - la copia de Home Assistant OS, de C2 del Día 3;
   - el binario del C6 con esptool, de A2;
   - las imágenes de los planes B y C (`docker save`);
   - un índice con los tamaños.
3. `instalar` y `verificar`:
   - en PowerShell para el portátil y en `.sh` para el escenario 1;
   - sin internet: `instalar` carga las imágenes con `docker load`.
   - Los `.sh` se prueban al menos en un contenedor de Linux o en WSL.
4. La guía del día de clase al día con D-22:
   - instalar los complementos (con el internet del celular si la Pi solo está en clase), con el paso que escribe B4;
   - copiar el modelo de Ollama y restaurar la copia de Home Assistant OS;
   - flashear la placa, con el paso que escribe A2;
   - correr `verificar`;
   - los planes B (escenario 2) y C, y los de siempre: el simulador, el registro manual y, si B2 lo deja, una cámara de respaldo.
5. Una prueba del kit:
   - `verificar` en verde contra la Pi o, si solo está en clase, contra el ensayo del devcontainer;
   - con el plan B, `verificar` en verde con el Compose de la carpeta principal;
   - cargar una imagen desde su `.tar` con internet apagado.
   - Sin bajar el Compose compartido con `-v`.
6. Documentación: `infra/README.md` (scripts, versiones y kit), `CLAUDE.md` (comandos nuevos), `specs/arquitectura.md` (versiones y Servicios), la guía y la bitácora.

## No hacer

- No subas el kit, las imágenes, el modelo, la copia de Home Assistant OS ni las claves al repositorio.
- No publiques el 8001 ni el 11434 de la Pi para que `verificar` los alcance (D-16).
- No bajes ni borres los volúmenes del Compose compartido: el arranque desde cero es del Día 5.
- No cambies el servidor, los complementos ni el firmware: son de B1, B4, A2 y A3.
- No cambies RNF-03 · C3, D-06 ni la guía sobre dónde corre Ollama sin proponerlo en el PR.

## Criterios de aceptación

- C1 (RF-11 · C1) `instalar` y `verificar` existen en PowerShell y en `.sh`, y `verificar` queda en verde contra la Pi o contra el ensayo del devcontainer.
- C2 (RF-11 · C2) El kit lleva todo lo de RF-11 · C2 con D-22, con su índice.
- C3 Las imágenes del plan B tienen versiones exactas en los Compose.
- C4 (RNF-04 · C3) El kit se usa sin internet, salvo para instalar los complementos, y las imágenes se cargan desde sus `.tar`.
- C5 La guía del día de clase dice los pasos reales con D-22 y los planes B y C; `infra/README.md`, `CLAUDE.md`, `arquitectura.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué lleva el kit y cuánto pesa;
  - qué revisa `verificar`, contra qué se probó y su resultado;
  - qué se decidió sobre `compose.ollama-portatil.yaml`;
  - qué falta para el ensayo del Día 5.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-c`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
