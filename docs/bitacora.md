<!--
Nombre: bitacora.md
Descripción: Bitácora de AccesIA: qué se hizo, quién, cómo (incluido el método con IA) y qué quedó pendiente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.3
-->

# Bitácora

Una entrada por tarea terminada, la más reciente arriba. Aquí se cuenta el método con IA; los commits y los PR no lo mencionan.

## Plantilla

```markdown
## AAAA-MM-DD · Día N · Tarea
- Quién:
- Qué: lo que quedó funcionando.
- Cómo: qué se le pidió a Claude Code, qué se revisó o corrigió a mano y qué decisiones se tomaron.
- Pruebas: cuáles corrieron y su resultado.
- Cambios de contrato o de specs: cuáles y por qué (o «ninguno»).
- Pendiente:
```

## 2026-11-11 · Día 1 · Horarios por bloques (D-20, contratos 1.2)

- Quién: el frente B.
- Qué: cada horario tiene ahora un nombre y bloques por día (día, hora de inicio y tolerancia), uno por día como máximo. Los contratos `base-de-datos.sql`, `openapi.yaml` y `mcp-agente.md` pasan a 1.2. También cambiaron D-20, R5 (con tres casos nuevos), RF-06 · C3, RF-09 · C2, el requisito nuevo RF-13, el modelo de datos, el plan (Día 2 de B y Día 3 de C), las tareas B y C del Día 1 y `web/README.md`.
- Cómo: el equipo decidió D-20 y Claude Code aplicó el cambio en la rama `b/horarios-1-2`, sin escribir código. Antes de seguir con la tarea B, Claude Code verificó el contrato.
- Decisiones menores al aplicar:
  - `horario_bloque` tiene como clave primaria `(horario_id, dia)`, sin un id propio, porque la API reemplaza la lista completa de bloques.
  - El mínimo de un bloque lo valida la API, no la base.
  - En la API, cada bloque pide su tolerancia; en la base, la tolerancia por defecto sigue siendo 10.
  - Un día repetido responde 422 `validacion`, y la lista admite como máximo 7 bloques.
  - El «por qué» de D-20 sale del ejemplo de lunes a las 07:00 y miércoles a las 18:00.
  - El horario de los casos nuevos de R5 se llama «Lunes y miércoles», con fechas de la semana del lunes 16 de noviembre de 2026.
  - En la tarea C, el horario de la persona se elige de la lista de horarios.
- Pruebas: `openapi.yaml` 1.2 pasa `openapi-spec-validator`. `base-de-datos.sql` 1.2 cargó en PostgreSQL 18.6 con pgvector, y pasaron las comprobaciones de los bloques, de la vista del agente y de los tres casos nuevos de R5. Se revisaron las referencias cruzadas.
- Cambios de contrato o de specs: los tres contratos pasan a 1.2 (registro de cambios en `specs/decisiones.md`). El esquema `Horario` cambia de campos, así que rompe la 1.1. Según `specs/contratos/README.md` eso sería 2.0, pero se dejó en 1.2 porque todavía no hay código que lo use.
- Pendiente: el plan de la tarea B, ajustado a los bloques; las preguntas 1 a 5 y 11 de la tarea 00.

## 2026-11-11 · Día 1 · AccesIA como raíz del repositorio

- Quién: el frente B.
- Qué: AccesIA quedó como raíz de su propio repositorio. Antes, el repositorio git estaba en la carpeta de arriba (`Inteligencia artificial/`) y el primer commit incluía otro proyecto de la materia (entrenamiento distribuido con TensorFlow). En GitHub, `main` se reemplazó con un push forzado y ahora solo tiene AccesIA.
- Cómo: lo detectó Claude Code al revisar las referencias cruzadas, porque GitHub solo corre los workflows de `.github/workflows/` en la raíz del repositorio. Propuso tres opciones y se eligió reescribir el mismo repositorio de GitHub, que era privado, solo tenía `main` y no tenía otros colaboradores. Pasos: respaldo con `git bundle` en `Universidad/respaldo-git-inteligencia-artificial-2026-11-11.bundle`; `git subtree split --prefix=AccesIA` de `main` y de `b/contratos-v1-1`; repositorio nuevo dentro de `AccesIA/`; `git push --force-with-lease` de `main` y push de `b/contratos-v1-1`.
- Pruebas: las ramas nuevas tienen el mismo árbol que `AccesIA/` en las viejas, con los mismos autores y fechas. En GitHub, `main` tiene la raíz de AccesIA y nada del otro proyecto, y el árbol de `b/contratos-v1-1` es igual al local.
- Cambios de contrato o de specs: ninguno. Los commits cambiaron de identificador: `4c3cca5` pasó a `cd480c4` y `915b0c2` a `8075dc0`.
- Pendiente: renombrar a `.git-viejo` el `.git` de la carpeta de arriba (falló porque VS Code estaba abierto). El proyecto de TensorFlow queda sin git; si lo quieren versionado, va en otro repositorio.

## 2026-11-11 · Día 1 · Tarea 00 · Contratos 1.1

- Quién: los tres integrantes acordaron en la tarea 00; el frente B aplicó los cambios en la rama `b/contratos-v1-1`.
- Qué: los acuerdos sobre la revisión de los contratos quedaron en las specs, los cinco contratos (versión 1.1), las tareas del Día 1, la guía del día de clase, `.gitignore` y `.editorconfig`. Se agregó `specs/contratos/casos-recorte.json` con los casos de la fórmula del recorte.
- Cómo: Claude Code hizo primero la revisión, sin cambiar archivos (`docs/revisiones/2026-11-11-revision-contratos-v1.md`). El equipo decidió punto por punto en la tarea 00. Después se le pidió a Claude Code aplicar esos acuerdos sin escribir código; las decisiones menores que tomó al aplicarlos quedan en la lista de abajo para revisarlas en el PR.
- Decisiones menores al aplicar: el código de error nuevo se llama `asistencia_duplicada` y el motivo nuevo de R7, `distinta_de_la_primera`. La asistencia de una persona se consulta en `GET /api/v1/personas/{persona_id}/asistencia`, y una llegada manual no puede tener hora futura. La tolerancia de 0,8 × `CARA_MIN_PX` se aplica al reconocer y al inscribir. En un `permitido` repetido, el mensaje MQTT lleva el `evento_id` original y la hora y la similitud del recorte nuevo. La ACL de `camara` agrega `topic deny accesia/servidor/#`. `EstadoCamara.firmware` usa el texto de la cabecera HTTP y el simulador no envía `perfil`, `rssi`, `psram_kb` ni `libre_kb`. El ejemplo de `ADMIN_CORREO` es `admin@example.com`. Los archivos nuevos se llaman `compose.ollama-portatil.yaml`, `automatizaciones_accesia.yaml`, `firmware.yml` y `compilar-binarios.ps1`. Las opciones del script de skills son `-Actualizar` y `--actualizar`. La fórmula del recorte redondea hacia afuera (piso al inicio y techo al final). También se arregló una descripción mal escrita del esquema `Error` de `openapi.yaml`, que creaba una clave suelta.
- Pruebas: `openapi.yaml` pasa `openapi-spec-validator` (OpenAPI 3.1). `base-de-datos.sql` 1.1 cargó en PostgreSQL 18.6 con pgvector (imagen `pgvector/pgvector:pg18`) y pasaron 11 comprobaciones: el código `servidor` se rechaza, `distinta_de_la_primera` se acepta como motivo, la asistencia guarda origen y autor, solo hay una llegada por día, y el usuario `agente` lee `v_asistencia_agente` (incluidas las llegadas manuales) pero no la tabla `asistencia`. Los dos casos de `casos-recorte.json` cumplen la fórmula. Se revisaron las referencias cruzadas: criterios RF, decisiones D, temas MQTT, variables, enums y columnas de las tablas Markdown.
- Cambios de contrato o de specs: los cinco contratos pasan a 1.1; el detalle está en el registro de cambios de `specs/decisiones.md`. Algunos cambios rompen la 1.0: `GET .../consentimiento` responde `null` en vez de 404 sin consentimiento vigente, las cámaras deben conectarse a MQTT con su código como client id, el 429 se mide con 0,8 s, `FilaAsistencia` pide `origen` y `registrado_por` y `EstadoCamara.firmware` cambia de formato. No afecta a nadie porque todavía no hay código.
- Pendiente: las preguntas 1, 2, 3, 4, 5 y 11 de la tarea 00 (quién consigue una placa antes de la clase). Revisar en el PR las decisiones menores de arriba.

## 2026-11-11 · Antes del Día 1 · Kit base del repositorio

- Quién: Cristhian Sánchez, para todo el equipo.
- Qué: `CLAUDE.md`, specs (enunciado, decisiones, arquitectura, requisitos, reglas, modelo de datos, consentimiento y plan), contratos (API, MQTT, agente y base de datos), tareas del Día 1, esta bitácora, la guía del día de clase y los diagramas.
- Cómo: las specs y los contratos se redactaron con Claude (claude.ai) a partir del levantamiento y del plan del proyecto. El equipo los revisa y los acepta en la tarea 00 del Día 1.
- Pruebas: `openapi.yaml` pasó `openapi-spec-validator`; `base-de-datos.sql` se cargó en un PostgreSQL 16 de prueba (con `vector` y `uuidv7` simulados) y se comprobaron restricciones, vistas, permisos del agente y borrado en cascada.
- Cambios de contrato o de specs: decisiones D-12 a D-19 propuestas.
- Pendiente: P-01 fecha de la clase; P-02 hardware que entregan; cargar el esquema en PostgreSQL 18 con pgvector (tarea B del Día 1).
