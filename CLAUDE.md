<!--
Nombre: CLAUDE.md
Descripción: Reglas e instrucciones para Claude Code en el repositorio de AccesIA.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# AccesIA — instrucciones para Claude Code

AccesIA es un control de acceso y asistencia con reconocimiento facial para la materia de Inteligencia Artificial (USCO).

- Una cámara ESP32-S3 detecta la cara con un modelo TinyML y envía solo el recorte.
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

## Hardware que todavía no tenemos

- La placa ESP32-S3 y la Raspberry llegan el día de la clase. Todo se desarrolla y se prueba con el simulador (`simulador/`), que cumple el mismo contrato que la cámara.
- No asumas pines, sensor de cámara ni tipo de PSRAM: el firmware se configura por perfiles de placa (`specs/arquitectura.md`).
- Las imágenes Docker se construyen para arm64 y amd64.

## Web

- Usa los skills de `.claude/skills/`: taste-skill completo, impeccable, los de Emil Kowalski y frontend-design. Se clonan con `scripts/preparar-skills.ps1` (Windows) o `scripts/preparar-skills.sh`, que crea la tarea C del Día 1.
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
├── firmware/              cámara ESP32-S3 (ESP-IDF, C++)             frente A
├── simulador/             cámara simulada con la webcam (Python)      frente A
├── servidor/              API, reconocimiento, reglas, MQTT y MCP     frente B
├── web/                   web de administración (React + Vite)        frente C
├── homeassistant/         configuración de Home Assistant             frente C
├── infra/                 Docker Compose, .env y scripts del kit      frentes B y C
└── scripts/               utilidades del repositorio
```

## Comandos

Se completan a medida que existan.
