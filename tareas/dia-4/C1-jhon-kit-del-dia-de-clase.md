<!--
Nombre: C1-jhon-kit-del-dia-de-clase.md
Descripción: Tarea C1 del Día 4 del frente C: el kit del día de clase en el portátil (RF-11), con D-21. Versiones fijas de las imágenes, imágenes en .tar, modelo de Ollama, copia de seguridad de Home Assistant OS, binario del C6, scripts instalar y verificar, y la guía del día de clase al día.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 4 · Frente C · C1 · El kit del día de clase

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/kit`
- Depende de:
  - B1 de hoy, para las imágenes: la web va dentro de la imagen del servidor;
  - C2 del Día 3: `compose.escenario2.yaml` y la copia de seguridad de Home Assistant OS;
  - A2 de hoy: el binario del C6 probado y sus pasos de flasheo;
  - A1 de hoy: los valores calibrados en `infra/.env.example`.
  - Los scripts y la guía pueden empezar antes, con lo que ya está en `main`.
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/requisitos.md`: RF-11, RNF-03 · C3 y RNF-04;
  - de `specs/decisiones.md`: D-04, D-06, D-09, D-19 y D-21, con «Lo que cambia en las decisiones anteriores con D-21»;
  - de `specs/arquitectura.md`: Servicios de Docker Compose y Red y despliegue;
  - `docs/guia-dia-de-clase.md`, `infra/README.md` y `homeassistant/README.md`.

## Objetivo

El kit del día de clase queda armado en el portátil y funciona sin internet (RF-11, RNF-04 · C3):

- las imágenes con versiones fijas;
- el modelo de Ollama;
- la copia de seguridad de Home Assistant OS;
- el binario del C6 con esptool;
- los scripts `instalar` y `verificar`.

`verificar` queda en verde con el Compose de la carpeta principal, y la guía del día de clase dice los pasos reales. El arranque desde cero con cronómetro es del ensayo del Día 5.

## Antes de empezar

- Propón en el plan:
  - **Qué scripts y en qué lenguaje.** Con D-21, la demo es el escenario 2: el portátil con Windows y Docker Desktop. Por eso `instalar` y `verificar` van en PowerShell para el portátil, y en `.sh` para el escenario 1 en Raspberry Pi OS, que es lo que nombra RF-11 · C1. Es la misma costumbre de `generar-env` y `crear-claves-mqtt`.
  - **Qué revisa `verificar`:**
    - los servicios y sus healthchecks;
    - `/api/v1/salud` con `base` y `mqtt` en `ok`;
    - que el MCP responde y que Ollama responde con el modelo cargado;
    - el descubrimiento retenido en el broker, del servidor y de la placa;
    - la placa en línea (`en_linea` de la cámara);
    - la web servida en `http://localhost:8000`.
    - Propón también qué hace si algo falla: dice qué y dónde mirar.
  - **`compose.ollama-portatil.yaml`.** Con D-21, Ollama ya corre en el portátil (D-06), así que este archivo solo serviría como plan B del escenario 1, si Ollama va lento en la Raspberry. Propón si se hace solo para eso o se quita del plan, de RNF-03 · C3, de D-19 y de la guía. Es un cambio de spec y se propone en el PR.
  - **Las versiones exactas de las imágenes**, que quedaron pendientes desde el Día 1: `pgvector/pgvector`, `eclipse-mosquitto`, `ollama/ollama` y la del servidor, fijadas en `infra/compose.yaml` y en `compose.escenario2.yaml`.
  - **Qué lleva `kit/` y cómo:**
    - las imágenes amd64 para el portátil, en `.tar`, y las arm64 solo para el escenario 1;
    - el modelo de Ollama, sin internet;
    - la copia de seguridad de Home Assistant OS;
    - el binario del C6 y esptool;
    - un índice con el tamaño de cada cosa. `kit/` lo ignora Git.
- Las claves no van en el kit: `infra/.env` se genera en el portátil con `generar-env`.

## Hacer

1. Las versiones fijas en los Compose, revisadas con `docker compose … config`.
2. El kit en `kit/`:
   - las imágenes (`docker save`), el modelo de Ollama, la copia de Home Assistant OS (de C2 del Día 3) y el binario del C6 con esptool (de A2);
   - un índice con los tamaños.
3. `instalar` y `verificar`:
   - en PowerShell para el portátil y en `.sh` para el escenario 1;
   - sin internet: cargan las imágenes con `docker load`.
   - Los `.sh` se prueban al menos en un contenedor de Linux o en WSL.
4. La guía del día de clase al día:
   - los pasos reales con los scripts;
   - quitar lo que D-21 dejó viejo, como Ollama en la Raspberry si se decide así;
   - los planes B con lo que ya existe (el simulador, el registro manual y, si B2 lo deja, una cámara de respaldo).
5. Una prueba del kit en el portátil:
   - `verificar` en verde con el Compose de la carpeta principal;
   - cargar una imagen desde su `.tar` con internet apagado.
   - Sin bajar el Compose compartido con `-v`.
6. Documentación: `infra/README.md` (scripts, versiones y kit), `CLAUDE.md` (comandos nuevos), `specs/arquitectura.md` (versiones y Servicios), la guía y la bitácora.

## No hacer

- No subas el kit, las imágenes, el modelo, la copia de Home Assistant OS ni las claves al repositorio.
- No bajes ni borres los volúmenes del Compose compartido: el arranque desde cero es del Día 5.
- No cambies el servidor ni el firmware: la web en la imagen es de B1, y el binario es de A2.
- No cambies RNF-03 · C3, D-19 ni la guía sobre Ollama sin proponerlo en el PR.

## Criterios de aceptación

- C1 (RF-11 · C1) `instalar` y `verificar` existen para el portátil y para el escenario 1, y `verificar` queda en verde en el portátil.
- C2 (RF-11 · C2) El kit lleva todo lo de RF-11 · C2 con D-21, sin internet, con su índice.
- C3 Las imágenes tienen versiones exactas en los Compose.
- C4 (RNF-04 · C3) Las imágenes se cargan desde el kit sin internet.
- C5 La guía del día de clase dice los pasos reales del escenario 2; `infra/README.md`, `CLAUDE.md`, `arquitectura.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué lleva el kit y cuánto pesa;
  - qué revisa `verificar` y su resultado;
  - qué se decidió sobre `compose.ollama-portatil.yaml`;
  - qué falta para el ensayo del Día 5.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-c`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
