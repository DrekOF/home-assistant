<!--
Nombre: CLAUDE.md
Descripción: Reglas e instrucciones para Claude Code en el repositorio de AccesIA.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.5
-->

# AccesIA — instrucciones para Claude Code

AccesIA es un control de acceso y asistencia con reconocimiento facial para la materia de Inteligencia Artificial (USCO).

- La cámara detecta la cara con un modelo TinyML y envía solo el recorte. Hoy la cámara es el simulador: la placa entregada, una XIAO ESP32-C6, todavía no tiene cámara y maneja la puerta y un sensor de temperatura y humedad (D-21).
- El servidor saca la huella de la cara (YuNet + SFace, 128 números) y la compara en PostgreSQL con pgvector.
- Home Assistant muestra lo que pasa, abre la puerta y avisa de desconocidos.
- Un agente con Ollama responde preguntas con herramientas de solo lectura.

Responde y escribe tus avisos en español.

## Antes de cada tarea

1. Lee `specs/README.md` y las specs que nombra la tarea. Los contratos de `specs/contratos/` mandan: el código se ajusta a ellos, no al revés.
2. Si algo no está en las specs o es ambiguo, pregunta antes de asumir. No inventes reglas, valores, campos ni temas MQTT.
3. Propón un plan corto y espera confirmación antes de cambios grandes.

## Reglas de trabajo

- Una rama y un PR por tarea. Nombre de la rama: `<frente>/<tarea-corta>`, por ejemplo `b/reconocimiento` (frentes: `a` cámara, `b` servidor, `c` web y despliegue).
- Pruebas primero en las reglas R1 a R9 (`specs/reglas.md`) y en los contratos. El nombre o la marca de cada prueba dice qué prueba, por ejemplo `RF-04 · C2` o `R5 · tarde`.
- Un contrato no se cambia en silencio: el cambio se propone en el PR, el equipo lo acepta y queda anotado en `specs/decisiones.md` y en el contrato, con su nueva versión.
- Al terminar cada tarea: una entrada en `docs/bitacora.md` (qué, quién, cómo, contando el método con IA) y las specs al día si algo cambió.
- Un PR se fusiona solo con las pruebas en verde.
- Al cerrar una tarea, resume en pocas líneas qué hiciste, qué pruebas corriste y su resultado, qué decidiste y qué queda pendiente.

## Autoría

- En GitHub solo aparecen como autores los integrantes del equipo. Nunca agregues a Claude como autor ni coautor de commits o PR: no escribas `Co-Authored-By` (`.claude/settings.json` ya lo desactiva).
- El cuerpo de un PR no nombra a Claude Code; el método con IA se cuenta en la bitácora.
- Cada archivo lleva un encabezado con nombre, descripción, fecha de creación, actualización, autor (`Equipo AccesIA`) y versión. Al modificar un archivo, actualiza su fecha de actualización y su versión. Los JSON no admiten comentarios y van sin encabezado. Los archivos generados (diagramas de Archify, lockfiles, tipos generados desde `openapi.yaml`) tampoco llevan encabezado.

Formatos del encabezado:

```text
Markdown y HTML   <!-- Nombre: … / Descripción: … / Fecha de creación: … / Actualización: … / Autor: Equipo AccesIA / Versión: … -->
Python            un docstring al inicio del módulo con los mismos campos
TS, TSX, JS, C++  un comentario /** … */ al inicio con los mismos campos
YAML, shell, PS1  líneas que empiezan con #
SQL               líneas que empiezan con --
```

## Privacidad y seguridad (no negociables)

- Nunca guardes imágenes de caras: ni en disco, ni en la base, ni en el repositorio. Solo se guardan huellas. La foto de un desconocido, si se muestra, se muestra en Home Assistant y no se guarda.
- No se inscribe a nadie sin su consentimiento registrado (Ley 1581 de 2012: los datos biométricos son sensibles).
- La puerta la abre una regla del servidor. El agente solo consulta, con un usuario de base de datos de solo lectura, y no tiene herramientas para cambiar nada.
- Nada de claves en el repositorio: van en `infra/.env`, que Git ignora. `infra/.env.example` lleva solo los nombres.
- Las fotos de prueba del equipo van en `datos/` (Git la ignora) y nunca se suben.

## Hardware

- Entregado el 12/11/2026 (D-21): una Seeed Studio XIAO ESP32-C6 (4 MB de flash, sin PSRAM ni interfaz de cámara) y una Raspberry Pi 5 con Home Assistant OS. El módulo de cámara llega la próxima clase (P-03).
- Hasta entonces, la cámara es el simulador (`simulador/`), que cumple el mismo contrato. Todo se sigue probando con él.
- Los pines de la XIAO ESP32-C6 están en `specs/arquitectura.md`; no asumas otros. El firmware del ESP32-S3, con sus perfiles de placa, queda como referencia en el PR #7.
- La demo usa el escenario 2: Docker Compose corre en el portátil, en el hotspot de Windows, y la Pi solo trae Home Assistant OS. Las imágenes Docker se siguen construyendo para arm64 y amd64.

## Web

- Usa los seis skills de `.claude/skills/`: taste-skill completo, impeccable, los de Emil Kowalski, frontend-design, refactoring-ui y web-design-guidelines. Se traen, en commits fijos, con `scripts/preparar-skills.ps1` (Windows) o `scripts/preparar-skills.sh`, que crea la tarea C del Día 1.
- web-design-guidelines se usa con la copia local de sus reglas, `.claude/skills/web-design-guidelines/command.md` (fijada en el commit `434b7f9` de `vercel-labs/web-interface-guidelines`). No se descarga de internet aunque el skill lo diga: así todas las sesiones revisan con las mismas reglas.
- De impeccable se usan solo sus guías: su ejecutable no se descarga ni se corre sin preguntarle antes al equipo.
- Al terminar una pantalla, verifícala con Playwright: que se vea y funcione como se planeó.
- Los tipos de la API se generan desde `specs/contratos/openapi.yaml`.

## Convenciones

- Todo en español: nombres del dominio (`persona`, `rostro`, `evento_acceso`), mensajes, comentarios y textos de la interfaz. Lo propio del framework queda en inglés.
- Fechas y horas en hora de Colombia (`America/Bogota`). En la API y en MQTT, ISO 8601 con zona (`2026-11-20T07:58:12-05:00`).
- Fin de línea LF (lo fija `.gitattributes`).
- El equipo trabaja en Windows con VS Code (terminal PowerShell) y Docker Desktop: da los pasos pensando en eso.
- No fijes el puerto 5432 de PostgreSQL en el PC: Windows puede tenerlo reservado. El puerto sale de `POSTGRES_PORT` en `infra/.env`.

## Estructura

```text
AccesIA/
├── CLAUDE.md              este archivo
├── specs/                 qué se construye: decisiones, arquitectura, requisitos, reglas, datos y plan
│   └── contratos/         API, MQTT, MCP del agente y base de datos (mandan sobre el código)
├── tareas/                tareas para Claude Code, por día y por frente
├── docs/                  bitácora, guía del día de clase y diagramas
├── firmware/              placa XIAO ESP32-C6 (ESP-IDF, C++)         frente A
├── simulador/             cámara simulada con la webcam (Python)      frente A
├── servidor/              API, reconocimiento, reglas, MQTT y MCP     frente B
├── web/                   web de administración (React + Vite)        frente C
├── homeassistant/         configuración de Home Assistant             frente C
├── infra/                 Docker Compose, .env y scripts del kit      frentes B y C
└── scripts/               utilidades del repositorio
```

## Comandos

Se completan a medida que existan. Desde la raíz del repositorio, en PowerShell:

```text
.\infra\scripts\generar-env.ps1                       crea infra/.env con claves nuevas (una vez)
.\infra\scripts\crear-claves-mqtt.ps1                 crea las claves de MQTT (una vez)
docker compose -f infra/compose.yaml up -d --build    levanta postgres, mosquitto y servidor
docker compose -f infra/compose.yaml ps               estado y healthchecks
docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador
                                                      registra una cámara y muestra su token una sola vez
curl.exe http://localhost:8000/api/v1/salud           prueba el servidor
docker compose -f infra/compose.yaml down             baja todo y conserva los datos
```

Desde `servidor/` (necesita uv y Docker Desktop abierto):

```text
uv sync                                               instala las dependencias
uv run accesia descargar-modelos                      descarga YuNet y SFace a datos/modelos/ y comprueba su SHA-256 (una vez)
uv run pytest                                         corre todas las pruebas, con su resumen por marca
uv run pytest -k acl                                  solo la ACL de MQTT (contrato MQTT · acl)
```

Desde `simulador/` (necesita uv; para enviar, el servidor arriba y la cámara creada con `crear-camara`):

```text
uv sync                                               instala las dependencias
uv run simulador modelo                               descarga YuNet a datos/modelos/ y comprueba su SHA-256 (una vez)
$env:TOKEN_CAMARA = "<token>"                         token de la cámara, solo en esta terminal
uv run simulador webcam --codigo entrada --como-camara
                                                      detecta con la webcam y envía; q o Esc para salir
uv run simulador carpeta datos/prueba --codigo entrada --como-camara
                                                      envía las fotos y las compara con su esperado.json
uv run pytest                                         corre las pruebas del simulador, con su resumen por marca
```

Skills de frontend, desde la raíz (después, reinicia Claude Code):

```text
.\scripts\preparar-skills.ps1                         trae los seis skills en sus commits fijos
.\scripts\preparar-skills.ps1 -Actualizar             trae la última versión y anota los commits nuevos
```

Desde `web/` (necesita Node 22.22 o más reciente):

```text
npm ci                                                instala las dependencias
npm run dev:simulacro                                 web en http://localhost:5173 con la API simulada
npm run dev                                           web con /api hacia el servidor en el puerto 8000
npm run tipos                                         regenera los tipos desde openapi.yaml
npm run build                                         revisa los tipos y compila
npm test                                              Vitest: lógica, simulacro y contraste
npm run e2e                                           Playwright con el simulacro; capturas en web/capturas/
```

Firmware de la XIAO ESP32-C6, desde la raíz (necesita ESP-IDF 5.4.4 y PowerShell, no Git Bash):

```text
.\firmware\scripts\compilar.ps1                       compila en firmware\build-c6
.\firmware\scripts\probar-logica.ps1                  pruebas de la lógica pura en ubuntu:24.04 (Docker Desktop)
idf.py -C firmware -B firmware\build-c6 -p COM5 flash monitor
                                                      flashea y abre la consola (Ctrl+] sale)
```

Más detalle en `infra/README.md`, `servidor/README.md`, `simulador/README.md`, `firmware/README.md`, `scripts/README.md` y `web/README.md`.
