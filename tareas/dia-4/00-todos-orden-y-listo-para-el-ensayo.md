<!--
Nombre: 00-todos-orden-y-listo-para-el-ensayo.md
Descripción: Día 4 para los tres integrantes: lo que sigue del Día 3 (Hito 1, C1, C2, A2 y el Hito 2), dependencias y orden entre las tareas A1, A2, B1, B2, B3, C1 y C2, reparto entre tres sesiones, acuerdos y lo que debe quedar listo para el ensayo del Día 5.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 4 · Todos · Orden del día y listo para el ensayo

El Día 4 deja todo listo para el ensayo general del Día 5. Primero termina lo que sigue del Día 3, con el Hito 2. Después vienen la calibración, la placa con Home Assistant, la web servida por el servidor, el modo extraer, la evaluación final del agente, el kit, Playwright y arm64.

## Tareas del día

| Tarea | Responsable | Rama | Depende de |
| --- | --- | --- | --- |
| [A1-julian-calibracion-del-umbral.md](A1-julian-calibracion-del-umbral.md) | Julián Andrés Silva Morales | `a/calibracion` | Las fotos de los tres en `datos/prueba/`, con su permiso, y un dataset público de impostores. Nada de B ni de C |
| [A2-julian-placa-con-home-assistant.md](A2-julian-placa-con-home-assistant.md) | Julián Andrés Silva Morales | `a/placa-home-assistant` | C2 del Día 3 en `main`, con Home Assistant OS configurado, y el Compose de la carpeta principal reconstruido con B2 del Día 3 |
| [B1-cristhian-web-en-el-servidor.md](B1-cristhian-web-en-el-servidor.md) | Cristhian Eduardo Sánchez Mosquera | `b/web-en-el-servidor` | Nada. Va primero, porque el kit (C1) la necesita |
| [B2-cristhian-modo-extraer.md](B2-cristhian-modo-extraer.md) | Cristhian Eduardo Sánchez Mosquera | `b/modo-extraer` | Nada. Comparte `servidor/accesia/main.py` con B1: el segundo PR trae `main` |
| [B3-cristhian-evaluacion-del-agente-y-cobertura.md](B3-cristhian-evaluacion-del-agente-y-cobertura.md) | Cristhian Eduardo Sánchez Mosquera | `b/evaluacion-agente` | La evaluación, de C2 del Día 3 (Assist con Ollama y MCP). La cobertura no espera a nadie |
| [C1-jhon-kit-del-dia-de-clase.md](C1-jhon-kit-del-dia-de-clase.md) | Jhon Jairo Perdomo Perdomo | `c/kit` | B1 (la web en la imagen), C2 del Día 3 (escenario 2 y copia de Home Assistant OS), A2 (el binario del C6 probado) y A1 (los valores calibrados). Los scripts y la guía pueden empezar antes |
| [C2-jhon-playwright-y-arm64.md](C2-jhon-playwright-y-arm64.md) | Jhon Jairo Perdomo Perdomo | `c/playwright-y-arm64` | Playwright, de C1 del Día 3 en `main` (todas las pantallas). arm64 no espera a nadie |

## Qué sigue del Día 3 al empezar

- **Ya en `main`:** A1, B1, B2 y B3 del Día 3 (PR #14 a #17), y el firmware del C6 (PR #11).
- **El Hito 1** está en curso y se termina primero.
- **C1 y C2 del Día 3** siguen en curso. C2 es la base del Hito 2 y de A2, B3 y C1 de hoy.
- **A2 del Día 3**, la cámara de la placa, sigue solo si llegó el módulo (P-03). Si no llegó, sigue esperando, y la cámara de la demo es el simulador (D-21).
- **El Hito 2** se corre apenas C2 del Día 3 esté en `main` y el Compose de la carpeta principal se haya reconstruido. Su guion está en `tareas/dia-3/00-todos-orden-e-hito-2.md`; lo que quede pendiente pasa a las tareas de hoy.
- **Pendientes de la bitácora que tienen tarea hoy:**
  - calibrar `UMBRAL_SIMILITUD` y `NITIDEZ_MIN`, en A1;
  - la lista «Por verificar» del firmware y la convivencia de la placa con `--puerta` del simulador, en A2;
  - el modo extraer, en B2;
  - la web servida por el servidor, que D-04 pedía y la imagen todavía no trae, en B1;
  - fijar las versiones exactas de las imágenes y armar la copia de seguridad de Home Assistant OS en el kit, en C1;
  - llevar Playwright a la CI, en C2.

## Orden

1. Terminar el Hito 1.
2. Terminar C2 del Día 3 (y C1 del Día 3, si falta) y correr el Hito 2.
3. Las tareas de hoy, en el orden de la tabla de turnos. B1 va primero en la sesión B, porque C1 arma las imágenes del kit con ella.

## Qué va en paralelo (tres sesiones)

| Turno | Sesión A | Sesión B | Sesión C |
| --- | --- | --- | --- |
| 1 | Hito 1 | Hito 1 | Hito 1 |
| 2 | A1 (calibración) | B1 (web en el servidor) y después B2 (modo extraer) | C2 del Día 3 y, si falta, C1 del Día 3 |
| 3 | Hito 2 | Hito 2 | Hito 2 |
| 4 | A2 (placa con Home Assistant) | B3 (evaluación del agente y cobertura) | C1 (kit) |
| 5 | A2 del Día 3, si llegó el módulo | B2, si falta | C2 (Playwright y arm64) |

- **Van en paralelo sin chocar:**
  - A1 con todo lo demás: solo toca `simulador/` y, al final, los valores calibrados.
  - B1 y B2 con todo, menos entre ellas: comparten `servidor/accesia/main.py`, y el segundo PR trae `main`.
  - C2 con todo: toca `web/` y `.github/workflows/web.yml`.
  - Lo de B3 que no necesita Home Assistant: la cobertura.
- **No van en paralelo:**
  - el Hito 2 antes de C2 del Día 3;
  - A2 y la evaluación de B3 antes del Hito 2, porque usan lo que deja C2;
  - las imágenes del kit (C1) antes de B1.
- **Orden para una misma persona:** si alguien hace varias tareas el mismo día, este orden evita bloqueos: B1, B2, B3, A1, A2, C1 y C2.

## Acuerdos para no pisarse

- **Docker Compose:**
  - corre solo desde la carpeta principal (`AccesIA`), que siempre está en `main`, y ninguna sesión lo levanta desde su worktree;
  - quien fusiona un PR que cambia el servidor, la web o la infra pregunta antes al equipo. Si hay un hito en curso, espera a que termine. Después hace `git pull` en la carpeta principal y lo reconstruye, avisando a las demás sesiones. Se levanta con `docker compose -f infra/compose.yaml up -d --build`, y con `-f infra/compose.escenario2.yaml` cuando exista;
  - durante un hito sí se fusiona, pero nadie hace `git pull` ni reconstruye en la carpeta principal hasta que termine;
  - las pruebas de cada tarea no lo necesitan: el servidor usa testcontainers, la web su simulacro y el simulador sus dobles. Las de punta a punta usan el de la carpeta principal y dejan los datos como estaban;
  - nadie baja el Compose compartido con `-v`: el arranque desde cero es del ensayo del Día 5.
- **Contratos:** nadie cambia uno sin proponerlo en su PR (`specs/contratos/README.md`). Hoy pueden cambiar:
  - `mcp-agente.md`, si la evaluación (B3) pide ajustar las instrucciones o las descripciones de las herramientas;
  - `api-dispositivo.md`, si el modo extraer (B2) necesita aclarar algo.
- **Archivos compartidos:**
  - `servidor/accesia/main.py`: B1 y B2;
  - `servidor/Dockerfile`: lo cambia B1, y C1 arma el kit con él;
  - `infra/.env.example`: A1 cambia los valores calibrados y C1 las versiones o lo que pida el kit. Cada uno anota lo suyo;
  - `docs/guia-dia-de-clase.md`: A2 escribe el flasheo de la placa y C1 el resto;
  - la bitácora y `specs/decisiones.md`: todos, y quien fusiona segundo conserva lo de los dos.
- **Datos:**
  - Las fotos de los integrantes siguen en `datos/prueba/`, con su permiso, y nunca se suben.
  - Un dataset público de impostores va en `datos/`, con su licencia anotada en la bitácora, y nunca en el repositorio.
  - Las imágenes, el kit y los binarios van en `kit/`, que Git ignora.
  - La semilla del agente convive con los datos reales como dice B3 del Día 3.

## Listo para el ensayo del Día 5

Al cerrar el día se revisa esta lista. Lo que falte se anota en la bitácora y pasa al Día 5, o al corte mínimo de `specs/plan.md` si la clase llega antes (P-01).

- L1 El Hito 2 cumplido, con su bitácora.
- L2 (D-04; RF-09 · C1) La web la sirve el servidor: el ensayo no necesita Node (B1).
- L3 (RNF-07) El umbral y la nitidez calibrados, en `infra/.env.example` y en `decisiones.md` (A1).
- L4 (RF-14; RF-07 · C2) La placa probada con Home Assistant OS, con el tiempo de la puerta medido (A2).
- L5 (RF-08 · C3) La evaluación final del agente con 9 de 10 o más, con la 9 y la 10 bien (B3).
- L6 (RF-11) El kit armado en el portátil y `verificar` en verde con el Compose de la carpeta principal (C1).
- L7 (RF-09 · C3) Playwright sobre toda la web en la CI (C2).

Las tareas del Día 5 (ensayo general e Hito 3) se escriben al cerrar el día, a partir de esta lista.

## Extras, si sobra tiempo

Los de `specs/plan.md` (Alcance) siguen sin tarea:

- registrar la salida;
- la foto del desconocido en Home Assistant, sin guardarla;
- el chat del agente en la web;
- varias cámaras;
- la página de presentación para la sustentación.

Quien tome uno lo propone primero, y nunca antes de lo obligatorio.
