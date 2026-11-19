<!--
Nombre: 00-todos-orden-y-listo-para-el-ensayo.md
Descripción: Día 4 para los tres integrantes, con D-22 (todo en la Raspberry Pi): lo que sigue del Día 3 (Hito 1, C1, C2, A2 y el Hito 2), qué necesita la placa y la Pi, dependencias y orden entre las tareas A1, A2, A3, B1, B2, B3, B4, C1 y C2, reparto entre tres sesiones, acuerdos y lo que debe quedar listo para el ensayo del Día 5.
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.2
-->

# Día 4 · Todos · Orden del día y listo para el ensayo

El Día 4 deja todo listo para el ensayo general del Día 5. Primero va el Hito 1. Con D-22, la demo pasa a la Raspberry Pi: la B4 hace los complementos de la base y del servidor, y el Hito 2 se hace en clase con ellos. Además vienen la calibración, la IP de la Pi en la placa y el simulador, la placa con Home Assistant, el modo extraer, la evaluación final del agente en la Pi, el kit, Playwright y arm64.

## Con qué se trabaja (D-22)

- **La demo corre en la Raspberry Pi 5 con Home Assistant OS:**
  - la base y el servidor, como complementos nuestros (B4);
  - el Mosquitto oficial, con nuestros usuarios y nuestra ACL;
  - Ollama, con el modelo que quepa en su RAM (P-04).
  - El detalle está en `specs/decisiones.md`, «Cómo se aplica D-22», y en `specs/arquitectura.md`, «Complementos de Home Assistant OS (D-22)».
- **El portátil** queda para desarrollar con Docker Compose, en la carpeta principal, y como plan B (el escenario 2 de D-21).
- **La placa y el simulador** apuntan a la IP fija de la Pi en el hotspot. Esa IP se confirma en clase (P-04), y los valores de fábrica pasan a ella en A3.
- **Lo que necesita la placa o la Pi:**
  - el Hito 2;
  - A2;
  - la parte de Home Assistant: C2 del Día 3 en la Pi, la evaluación de B3 y la copia de Home Assistant OS del kit (C1).

  Si el hardware solo está disponible en clase, esos turnos se mueven al día de clase, y lo demás sigue sin esperar.

## Tareas del día

| Tarea | Responsable | Rama | Depende de |
| --- | --- | --- | --- |
| [A1-julian-calibracion-del-umbral.md](A1-julian-calibracion-del-umbral.md) | Julián Andrés Silva Morales | `a/calibracion` | Las fotos de quienes participen (los tres integrantes y quien más quiera), cada uno con su consentimiento (Ley 1581), y un dataset público de impostores con una licencia que permita este uso. Nada de B ni de C |
| [A2-julian-placa-con-home-assistant.md](A2-julian-placa-con-home-assistant.md) | Julián Andrés Silva Morales | `a/placa-home-assistant` | La placa y la Pi; C2 del Día 3 y B4 en `main`, o el escenario 2 si no alcanzan; el Hito 2. El binario del kit, después de A3 |
| [A3-julian-ip-de-la-pi.md](A3-julian-ip-de-la-pi.md) | Julián Andrés Silva Morales | `a/ip-de-la-pi` | D-22 en `main`. La IP fija de la Pi se confirma en clase (P-04); mientras tanto se usa la del ejemplo de D-22 |
| [B1-cristhian-web-en-el-servidor.md](B1-cristhian-web-en-el-servidor.md) | Cristhian Eduardo Sánchez Mosquera | `b/web-en-el-servidor` | Ya en `main` (PR #19) |
| [B2-cristhian-modo-extraer.md](B2-cristhian-modo-extraer.md) | Cristhian Eduardo Sánchez Mosquera | `b/modo-extraer` | Nada. Parte de `main`, que ya trae B1 |
| [B3-cristhian-evaluacion-del-agente-y-cobertura.md](B3-cristhian-evaluacion-del-agente-y-cobertura.md) | Cristhian Eduardo Sánchez Mosquera | `b/evaluacion-agente` | La evaluación: la Pi, C2 del Día 3 y B4 (Assist con Ollama en la Pi y el MCP del complemento del servidor). La cobertura no espera a nadie |
| [B4-cristhian-complementos-de-la-base-y-del-servidor.md](B4-cristhian-complementos-de-la-base-y-del-servidor.md) | Cristhian Eduardo Sánchez Mosquera | `b/complementos` | D-22 en `main` (PR #20). No necesita la Pi: se prueba en la CI, en el portátil y en el devcontainer |
| [C1-jhon-kit-del-dia-de-clase.md](C1-jhon-kit-del-dia-de-clase.md) | Jhon Jairo Perdomo Perdomo | `c/kit` | B4 (las carpetas de los complementos), C2 del Día 3 (Ollama en la Pi, la copia de Home Assistant OS y el escenario 2), A2 (el binario probado), A3 (la IP de la Pi) y A1 (los valores calibrados). Los scripts y la guía pueden empezar antes |
| [C2-jhon-playwright-y-arm64.md](C2-jhon-playwright-y-arm64.md) | Jhon Jairo Perdomo Perdomo | `c/playwright-y-arm64` | Playwright, de C1 del Día 3 en `main` (todas las pantallas). arm64 no espera a nadie |

## Qué sigue del Día 3 al empezar

- **Ya en `main`:**
  - A1, B1, B2 y B3 del Día 3 (PR #14 a #17) y el firmware del C6 (PR #11);
  - B1 de hoy, la web servida por el servidor (PR #19);
  - D-22 (PR #20), con `mqtt.md` 1.4 y `mcp-agente.md` 1.4;
  - el contrato del agente 1.5 (PR #21): `fecha_y_hora_GetDateTime`, para que Ollama reutilice el comienzo del prompt entre preguntas.
- **El Hito 1** todavía no empieza. Va primero, con `main` al día: el Compose de la carpeta principal ya está reconstruido con B2 del Día 3 y la web servida por el servidor.
- **C1 y C2 del Día 3** siguen en curso. C2, ajustada a D-22, es la base del Hito 2 y de A2, B3 y C1 de hoy. Lo que no espera a la B4 (Mosquitto, Ollama y los archivos de Home Assistant) puede empezar ya.
- **A2 del Día 3**, la cámara de la placa, sigue solo si llegó el módulo (P-03). Si no llegó, sigue esperando, y la cámara de la demo es el simulador (D-21).
- **Pendientes de la bitácora que tienen tarea hoy:**
  - calibrar `UMBRAL_SIMILITUD` y `NITIDEZ_MIN`, en A1;
  - pasar a la IP de la Pi los valores de fábrica del firmware y los ejemplos del simulador, en A3;
  - la lista «Por verificar» del firmware y la convivencia de la placa con `--puerta` del simulador, en A2;
  - el modo extraer, en B2;
  - los complementos, su CI y la ACL de `mqtt.md` 1.4, en B4;
  - fijar las versiones exactas de las imágenes y armar la copia de seguridad de Home Assistant OS en el kit, en C1;
  - llevar Playwright a la CI, en C2.

## El Hito 2

- Se hace en clase con D-22, cuando estén en `main` la B4 de hoy y la C2 del Día 3.
- Si para esa clase no alcanzan, se prueban MQTT y Home Assistant con el escenario 2, y el agente queda para cuando la B4 esté lista.
- Su guion es el de `tareas/dia-3/00-todos-orden-e-hito-2.md`:
  - con D-22, lo que allí corre en el portátil corre en la Pi, como complementos;
  - con el escenario 2, se sigue tal cual, sin los pasos del agente.
- Lo que quede pendiente pasa a la bitácora y a las tareas de hoy.

## Orden

1. El Hito 1.
2. Lo que no necesita la placa ni la Pi: B4, A1, A3, B2, la cobertura de B3, Playwright, y los scripts y la guía de C1. También lo de C2 del Día 3 que se ensaya en el devcontainer.
3. Con la placa y la Pi, en clase si solo están allá: el Hito 2, A2, la evaluación de B3, lo de C2 del Día 3 en la Pi y la copia de Home Assistant OS.
4. El kit (C1), con todo lo anterior.

## Qué va en paralelo (tres sesiones)

| Turno | Sesión A | Sesión B | Sesión C |
| --- | --- | --- | --- |
| 1 | Hito 1 | Hito 1 | Hito 1 |
| 2 | A1 (calibración) | B4 (complementos) | C2 del Día 3: lo que no espera a la B4 y, si falta, C1 del Día 3 |
| 3 | A3 (la IP de la Pi) | B2 (modo extraer) y la cobertura de B3 | C2 de hoy: Playwright; los scripts y la guía de C1 |
| 4, con la placa y la Pi | Hito 2 y A2 | Hito 2 y la evaluación de B3 | Hito 2, C2 del Día 3 en la Pi y la copia de Home Assistant OS |
| 5 | A2 del Día 3, si llegó el módulo | B2, si falta | C1 (kit) y el arm64 de C2 |

- **Si la placa y la Pi solo están en clase,** el turno 4 se mueve al día de clase, y los turnos 2, 3 y 5 siguen sin esperar. Lo que en el turno 5 necesite el turno 4 queda para después de la clase.
- **Van en paralelo sin chocar:**
  - A1 con todo lo demás: solo toca `simulador/` y, al final, los valores calibrados.
  - A3 con todo, menos con A2: las dos tocan `firmware/`, y la segunda trae `main`.
  - B4 y B2, en dos sesiones de B si las hay. Si tocan el mismo archivo, la segunda trae `main`.
  - C2 con todo: toca `web/` y `.github/workflows/web.yml`.
  - Lo de B3 que no necesita Home Assistant: la cobertura.
- **No van en paralelo:**
  - el Hito 2 antes de la B4 y de C2 del Día 3, salvo con el escenario 2 y sin el agente;
  - A2 y la evaluación de B3 antes del Hito 2, porque usan lo que deja C2;
  - el kit (C1) antes de la B4, que arma las carpetas de los complementos;
  - el binario del kit antes de A3, que cambia los valores de fábrica.
- **Orden para una misma persona:** si alguien hace varias tareas el mismo día, este orden evita bloqueos: B4, B2, B3, A1, A3, A2, C1 y C2.

## Acuerdos para no pisarse

- **Docker Compose:**
  - con D-22, la demo corre en la Pi, y el Compose sigue para desarrollar, para los hitos con el escenario 2 y como plan B;
  - corre solo desde la carpeta principal (`AccesIA`), que siempre está en `main`, y ninguna sesión lo levanta desde su worktree;
  - quien fusiona un PR que cambia el servidor, la web o la infra pregunta antes al equipo. Si hay un hito en curso, espera a que termine. Después hace `git pull` en la carpeta principal y lo reconstruye, avisando a las demás sesiones. Se levanta con `docker compose -f infra/compose.yaml up -d --build`, y con `-f infra/compose.escenario2.yaml` cuando exista;
  - durante un hito sí se fusiona, pero nadie hace `git pull` ni reconstruye en la carpeta principal hasta que termine;
  - las pruebas de cada tarea no lo necesitan: el servidor usa testcontainers, la web su simulacro y el simulador sus dobles. Las de punta a punta usan el de la carpeta principal y dejan los datos como estaban;
  - nadie baja el Compose compartido con `-v`: el arranque desde cero es del ensayo del Día 5.
- **Contratos:** nadie cambia uno sin proponerlo en su PR (`specs/contratos/README.md`). Hoy pueden cambiar:
  - `mcp-agente.md`, si la evaluación (B3) pide ajustar las instrucciones o las descripciones de las herramientas, por ejemplo para acortarlas en la Pi (D-22);
  - `api-dispositivo.md`, si el modo extraer (B2) necesita aclarar algo.
  - `mqtt.md` ya está en 1.4 con D-22: la B4 solo pone al día la ACL y su prueba.
- **Archivos compartidos:**
  - `servidor/accesia/main.py`: B2. B1 ya está en `main`;
  - `servidor/Dockerfile`: ya lo cambió B1, y la B4 parte de él para el complemento del servidor;
  - `infra/mosquitto/acl` y la prueba `contrato MQTT · acl`: B4. C2 del Día 3 copia esa ACL a la Pi;
  - `firmware/`: A3 y A2, y la segunda trae `main`;
  - `infra/.env.example`: A1 cambia los valores calibrados y C1 las versiones o lo que pida el kit. Cada uno anota lo suyo;
  - `docs/guia-dia-de-clase.md`: A2 escribe el flasheo de la placa, B4 la instalación de los complementos y C1 el resto;
  - `kit/`: B4 arma `kit/complementos/` y C1 todo lo demás;
  - la bitácora y `specs/decisiones.md`: todos, y quien fusiona segundo conserva lo de los dos.
- **Datos:**
  - Las fotos de quienes participen en la calibración (los tres integrantes y quien más quiera) van en `datos/prueba/`, cada una con el consentimiento de su titular (Ley 1581), y nunca se suben.
  - El dataset público de impostores va en `datos/`, con una licencia que permita este uso. Nunca va al repositorio y se borra al terminar la calibración. La bitácora anota cuál fue, su licencia y que se borró.
  - Las imágenes, el kit y los binarios van en `kit/`, que Git ignora.
  - Las copias de Home Assistant OS llevan las huellas: van cifradas y nunca al repositorio, y la del kit se toma sin inscripciones (D-22).
  - La semilla del agente convive con los datos reales como dice B3 del Día 3.

## Listo para el ensayo del Día 5

Al cerrar el día se revisa esta lista. Lo que falte se anota en la bitácora y pasa al Día 5, o al corte mínimo de `specs/plan.md` si la clase llega antes (P-01).

- L1 El Hito 2 cumplido con D-22, con su bitácora. Si se hizo con el escenario 2, queda anotado que el agente espera a la B4.
- L2 (D-04; RF-09 · C1) La web la sirve el servidor: el ensayo no necesita Node (B1, ya en `main`).
- L3 (RNF-07) El umbral y la nitidez calibrados, en `infra/.env.example` y en `decisiones.md` (A1).
- L4 (D-22) Los valores de fábrica de la placa y los ejemplos del simulador en la IP de la Pi (A3).
- L5 (RF-14; RF-07 · C2) La placa probada con Home Assistant OS, con el tiempo de la puerta medido (A2).
- L6 (D-22; D-11) Los complementos de la base y del servidor, con `complementos.yml` en verde y la ACL de `mqtt.md` 1.4 (B4).
- L7 (RF-08 · C3) La evaluación final del agente en la Pi con 9 de 10 o más, con la 9 y la 10 bien, y el modelo fijado según su RAM (B3).
- L8 (RF-11) El kit armado con D-22, y `verificar` en verde contra la Pi o, si solo está en clase, contra el ensayo del devcontainer (C1).
- L9 (RF-09 · C3) Playwright sobre toda la web en la CI (C2).

Las tareas del Día 5 (ensayo general e Hito 3) se escriben al cerrar el día, a partir de esta lista.

## Extras, si sobra tiempo

Los de `specs/plan.md` (Alcance) siguen sin tarea:

- registrar la salida;
- la foto del desconocido en Home Assistant, sin guardarla;
- el chat del agente en la web;
- varias cámaras;
- la página de presentación para la sustentación.

Quien tome uno lo propone primero, y nunca antes de lo obligatorio.
