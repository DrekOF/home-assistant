<!--
Nombre: bitacora.md
Descripción: Bitácora de AccesIA: qué se hizo, quién, cómo (incluido el método con IA) y qué quedó pendiente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.5
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

## 2026-11-11 · Día 1 · Tarea C · Skills de frontend y web base

- Quién: el frente C.
- Qué:
  - `scripts/preparar-skills.ps1` y `.sh` traen los seis skills de frontend a `.claude/skills/`, cada uno en su commit fijo. También traen la copia local de las reglas de web-design-guidelines (`command.md`, commit `434b7f9` de `vercel-labs/web-interface-guidelines`). Tienen la opción `-Actualizar` (`--actualizar` en Bash), anotan cada commit en `VERSIONES.txt` y no cambian nada si algo falla.
  - `web/` queda con React 19, Vite 8, React Router 8, TanStack Query 5 y `openapi-fetch`, con los tipos generados desde `openapi.yaml`. Tiene el simulacro de la API con MSW 3 y estas pantallas:
    - Inicio de sesión.
    - Personas: búsqueda sin tildes, filtro y paginación guardados en la dirección, y activar o desactivar con «Deshacer».
    - Formulario para crear y editar: el horario se elige de la lista, con el resumen de sus bloques, y avisa antes de salir con cambios sin guardar.
    - Ficha con el consentimiento: texto de la API, aviso de que es opcional, registro en web o en papel, revocación confirmada e historial. «Inscribir» solo se habilita con consentimiento vigente.
    - «Próximamente» en las otras cinco secciones.
  - La CI de la web quedó en `.github/workflows/web.yml`.
- Cómo:
  - Claude Code propuso el plan y la dirección visual. El equipo la aprobó con lucide-react para los íconos y con las reglas de web-design-guidelines fijadas en `434b7f9`. De impeccable se usaron solo sus guías; su ejecutable no se corrió.
  - Skills: se revisó qué trae cada repositorio antes de fijar su commit. El script se probó en PowerShell 5.1 y en Git Bash: los dos dejan los mismos 1.727 archivos, byte a byte. En copias del script se probó `--actualizar` con commits viejos simulados y también una ruta que cambió: avisa dónde quedó la carpeta, sale con código 1 y no toca nada.
  - Errores que aparecieron y se corrigieron:
    - En Bash, `grep -q` dentro de una tubería con `pipefail` daba SIGPIPE en los repositorios grandes. Se cambió a here-strings.
    - En Git Bash, `sed` y `awk` quitan los CR del `.ps1`. La tabla se actualiza con Bash puro.
    - `openapi-typescript` volvía obligatorios los campos con valor por defecto (`activa`, `medio`). Se genera con `--default-non-nullable false`.
    - Se usa TypeScript 5.9, porque `openapi-typescript` 7 pide TypeScript 5.
    - En MSW 3, `onUnhandledRequest` pasó a llamarse `onUnhandledFrame`.
    - El simulacro entraba al paquete de producción. Ahora una constante de compilación (`__SIMULACRO__`) lo saca.
    - Playwright encontró un error real: si el filtro cambiaba mientras la búsqueda esperaba, el filtro se perdía.
    - La prueba de teclado encontró otro: después de entrar, el foco quedaba perdido.
    - Los espacios duros (U+00A0) que escribía la herramienta llegaban al código como caracteres invisibles. Se dejaron como secuencias de escape, que se ven.
  - Revisión visual: Claude Code revisó las capturas de cada pantalla a 1280×720 y 1440×900. Se corrigieron estos problemas:
    - la columna Datos era angosta;
    - salían el punto doble «a. m..» y la hora partida entre «a.» y «m.»;
    - una insignia larga aplastaba el historial;
    - la barra lateral se veía cortada en las capturas de página completa;
    - la tabla tenía subrayados de más.
  - Accesibilidad: revisión con la copia local de `command.md`. Se cambió la paginación a enlaces, se pusieron espacios duros en «10 min», se agregó `autocomplete` y se escribió una prueba automática del contraste AA.
- Decisiones:
  - El script de skills es todo o nada: si un repositorio falla, no se cambia ninguno.
  - El simulacro vive en la memoria de la pestaña, con datos ficticios. Sus credenciales de prueba (`admin@example.com` y `simulacro`) solo existen en él.
  - «Inscribir» es un botón y no un enlace, porque debe poder deshabilitarse (RF-02 · C4).
  - Los títulos y botones van en mayúscula solo en la primera palabra, como se escribe en español, aunque web-design-guidelines pide *Title Case*.
  - Los tokens, los componentes y el skill que apoya cada decisión quedan en `web/DESIGN.md`.
- Pruebas:
  - `npm test` (Vitest): 68 en verde, entre fechas en hora de Colombia, validaciones, horarios, texto, el simulacro contra el contrato y el contraste AA.
  - `npm run e2e` (Playwright con el simulacro): 9 en verde, incluidas la prueba de teclado y las capturas.
  - `npm run build` en verde, sin el simulacro en el paquete. `npm run tipos` regenera los tipos sin cambios.
  - Script de skills: cinco corridas manuales. Instalación normal y `--actualizar` en PowerShell 5.1 y en Bash, más una ruta que cambió.
- Cambios de contrato o de specs: ninguno en los contratos. Antes de empezar, D-11 pasó a seis skills, y se actualizaron la tarea C, `CLAUDE.md` (sección Web) y el extra de `plan.md`. Al terminar, `CLAUDE.md` sumó los comandos de los skills y de la web.
- Pendiente:
  - Ver `web.yml` en verde en el PR (C7).
  - Llevar Playwright a la CI el Día 4.
  - Conectar la web con el servidor real cuando la tarea B del Día 2 tenga sesión y personas.
  - `public/mockServiceWorker.js` también se copia a `dist/`. No se registra sin simulacro, pero se puede excluir cuando el servidor sirva la web.

## 2026-11-11 · Día 1 · Tarea B · Docker Compose, base de datos y esqueleto del servidor

- Quién: el frente B.
- Qué: con `docker compose -f infra/compose.yaml up -d --build` quedan sanos `postgres` (PostgreSQL 18 + pgvector), `mosquitto` y `servidor`, con el esquema del contrato 1.2 migrado y `/api/v1/salud` respondiendo. También quedaron los scripts `generar-env` y `crear-claves-mqtt` (`.ps1` con BOM y `.sh`), 24 pruebas con pytest y la CI en `.github/workflows/servidor.yml`.
- Cómo: se le pidió a Claude Code un plan corto, ajustado a los horarios por bloques (D-20), y el equipo lo aprobó con un cambio: la ACL de Mosquitto se comprueba con una prueba automática (`contrato MQTT · acl`) y no con un paso manual. Claude Code instaló uv con winget, escribió el código y lo verificó. Para confirmar que las pruebas de la ACL no pasan siempre, rompió la ACL a propósito tres veces: quitó la línea `deny`, abrió el estado de todas las cámaras y permitió el acceso anónimo. Cada vez falló justo la prueba que correspondía, y después dejó los archivos como estaban.
- Decisiones:
  - La migración ejecuta el SQL con el cursor de psycopg, sin parámetros, dentro de la transacción de Alembic. La imagen copia el SQL a la misma ruta relativa que en el repositorio, y la migración lo busca subiendo carpetas. Si el usuario `agente` ya existe, le actualiza la clave.
  - El 405 se responde con `no_encontrado`, porque el contrato no tiene un código para «método no permitido».
  - FastAPI no publica su propio OpenAPI: el contrato es `specs/contratos/openapi.yaml`.
  - El paquete arranca en la versión `0.1.0`. `config.py` solo exige `DATABASE_URL`; las reglas tienen los valores de `arquitectura.md` por defecto.
  - Cada prueba lleva `@pytest.mark.marca("…")`: pytest no corre si alguna no la tiene, y al final muestra un resumen por marca.
  - El healthcheck de Mosquitto entra con el usuario `servidor` usando `mosquitto_sub -E`.
  - `mosquitto_passwd -c` no sobrescribe un archivo existente, así que los scripts borran `passwd` antes de crearlo. Ese error salió al correrlos dos veces.
- Pruebas:
  - `uv run pytest`: 24 en verde. Por marca: esquema 1, vector 1, horarios 5, RF-08 · C4 7, salud 1, error 3 y ACL de MQTT 6.
  - Compose: los tres servicios sanos; PostgreSQL publicado solo en `127.0.0.1:5434`, con los datos en `/var/lib/postgresql/18/docker`; migración `0001` aplicada una sola vez, incluso tras reiniciar.
  - El usuario `agente` entra con la clave de `infra/.env`.
  - Los cuatro scripts funcionan y se pueden correr varias veces.
  - La imagen también compila para `linux/arm64`.
- Cambios de contrato o de specs: ninguno. `CLAUDE.md` tiene ahora la sección «Comandos».
- Pendiente:
  - Ver la CI en verde en el PR (C7).
  - Starlette avisa que `TestClient` con `httpx` está en desuso y pide `httpx2`; la tarea nombra `httpx`, así que se dejó así.
  - Fijar las versiones exactas de las imágenes el Día 4.

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
