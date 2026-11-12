<!--
Nombre: B1-cristhian-sesion-y-api.md
Descripción: Tarea B1 del Día 2 del frente B: sesión y primer administrador; API de personas, consentimiento, horarios y cámaras; comando crear-camara; contrato 1.3 con metodo_no_permitido e inscripcion_activa.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 2 · Frente B · B1 · Sesión y API de administración

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/sesion-y-api`
- Lee primero: `CLAUDE.md`; `tareas/dia-2/00-todos-orden-e-hito-1.md`; `specs/contratos/openapi.yaml` (Sesión, Personas, Consentimiento, Horarios y Cámaras, con sus esquemas); `specs/contratos/README.md` (cómo cambia un contrato); `specs/requisitos.md` (RF-02, RF-10, RF-12 · C2, RF-13 y RNF-02); `specs/reglas.md` (R3, R8 y R9, por la revocación); `specs/modelo-datos.md`; `specs/consentimiento.md`; `specs/arquitectura.md` (Configuración); `specs/decisiones.md` (D-07, D-13 y D-20); `servidor/README.md`.

## Objetivo

La web puede iniciar sesión y trabajar contra el servidor real con personas, consentimiento, horarios y cámaras. El comando `crear-camara` registra una cámara sin pasar por la web. El contrato de la API pasa a 1.3: el código `metodo_no_permitido` para el 405 y el campo `inscripcion_activa` de las cámaras, para que la web encuentre la inscripción activa de una cámara aunque haya perdido su id.

## Hacer

1. Contrato 1.3, primero, porque cambia un contrato (`specs/contratos/README.md`):
   - En `openapi.yaml`:
     - Agrega `metodo_no_permitido` al enum `codigo` de `Error`.
     - Agrega a `Dispositivo` el campo `inscripcion_activa`: la inscripción activa de la cámara como `InscripcionCorta`, o `null` si no tiene. Va en `required`, como los demás campos de `Dispositivo`, y `DispositivoConToken` lo hereda. `modo` es `inscribir` si y solo si `inscripcion_activa` no es `null`.
     - Sube la versión a 1.3 (encabezado e `info.version: 1.3.0`). Los dos cambios solo agregan: nada de lo que ya existe cambia.
   - Anota el cambio en el registro de `specs/decisiones.md`, en la tabla de `specs/contratos/README.md` y en una sección «Versión 1.3» de ese README.
   - En `accesia/errores.py`, el 405 responde `metodo_no_permitido` y `CodigoError` suma el código.
   - Regenera los tipos de la web con `npm run tipos` en `web/` y súbelos en este PR: `web.yml` falla si `esquema.d.ts` no coincide con el contrato. No toques nada más de `web/`.
   - El PR lo aprueban A y C, que usan este contrato.
2. Sesión y primer administrador (RNF-02 · C2 y C5):
   - `POST`, `GET` y `DELETE /api/v1/sesion`. La cookie `accesia_sesion` va con `HttpOnly`, `SameSite=Strict` y `Path=/`, firmada con `SESION_SECRETO`. Las claves se guardan y se comprueban con Argon2id.
   - El correo no distingue mayúsculas. Un correo que no existe, una clave equivocada o un administrador inactivo responden 401 `credenciales_invalidas`, sin decir cuál de los tres.
   - Todas las rutas piden sesión, menos `GET /api/v1/salud` y `POST /api/v1/sesion`. Sin sesión: 401 `sin_sesion`.
   - Al arrancar, si no existe un administrador con `ADMIN_CORREO`, se crea con `ADMIN_CLAVE_INICIAL`. Si ya existe, su clave no se toca.
   - Las specs no dicen el nombre de ese administrador ni cuánto dura la sesión: propón los dos en el plan.
3. Personas (RF-02 · C1, RF-12 · C2):
   - `GET` y `POST /api/v1/personas`; `GET`, `PATCH` y `DELETE /api/v1/personas/{persona_id}`, con los esquemas `Persona`, `PersonaNueva`, `PersonaCambios` y `PaginaPersonas`.
   - `q` busca en nombre y documento sin importar tildes ni mayúsculas (`unaccent`), con `%` y `_` escapados.
   - `muestras` es la cantidad de huellas. `consentimiento_vigente` y `horario_nombre` salen de sus tablas.
   - Documento repetido: 409 `documento_duplicado`. Al borrar una persona, sus eventos quedan sin persona (lo hace la base).
   - Donde el contrato no dice nada, responde como el simulacro de la web (`web/src/simulacro/manejadores.ts`): orden por nombre, un horario que no existe es 422 `validacion` y un `PATCH` vacío también. Si no estás de acuerdo, se discute en el PR.
4. Consentimiento (RF-02 · C2 y C5, D-07):
   - `GET /api/v1/consentimiento/texto` lee `specs/consentimiento.md` como el simulacro: el texto entre las dos líneas `---` y la versión del título («versión del texto 1.0»).
   - El `Dockerfile` copia `specs/consentimiento.md` a la misma ruta relativa, como ya hace con el SQL.
   - `GET`, `POST` y `DELETE /api/v1/personas/{persona_id}/consentimiento`, y `GET …/consentimientos`.
   - `POST`:
     - Versión distinta de la vigente: 422 `version_texto_invalida`.
     - Ya hay uno vigente: 409 `consentimiento_vigente`.
     - `aceptado_en` solo con medio papel y no futura; si no, 422 `validacion`.
     - `registrado_por` es el administrador de la sesión, y la respuesta da su nombre.
   - `DELETE`: en una sola transacción marca `revocado_en`, borra las huellas de la persona y cancela su inscripción activa (RF-02 · C5, R9). Sin consentimiento vigente: 404.
5. Horarios por bloques (RF-13 · C1 a C3, D-20):
   - `GET` y `POST /api/v1/horarios`; `PATCH` y `DELETE /api/v1/horarios/{horario_id}`.
   - Los bloques salen ordenados por día. Un `PATCH` con `bloques` reemplaza la lista completa.
   - Día repetido, lista vacía o más de 7 bloques: 422 `validacion`. Nombre repetido: 409 `nombre_duplicado`.
   - Horario en uso: 409 `horario_en_uso`, traducido del `restrict_violation` (SQLSTATE 23001), como dice `contratos/README.md`.
6. Cámaras (RF-10 · C1 a C3):
   - `GET` y `POST /api/v1/dispositivos`; `GET` y `PATCH /api/v1/dispositivos/{codigo}`; `POST /api/v1/dispositivos/{codigo}/token`.
   - El token tiene 32 bytes aleatorios. Se guarda su SHA-256 en hexadecimal y se muestra una sola vez: al crear la cámara y al cambiarlo. Nunca va en los registros.
   - El código `servidor`, o el tipo `respaldo` sin `url_captura`: 422 `validacion`. Código repetido: 409 `codigo_duplicado`.
   - Antes de listar o ver cámaras, vence las inscripciones activas que ya pasaron su hora (R9) y calcula `modo` e `inscripcion_activa`. Deja esa función lista para que B2 la use.
   - `en_linea`: hasta que llegue MQTT (Día 3), solo cuenta «un contacto en los últimos 2 minutos». `estado` es `null` hasta el Día 3.
7. Comando `crear-camara` (RF-10 · C5): un comando `accesia` del paquete, con esta forma, que es la que usa el guion del Hito 1:

   ```powershell
   docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador
   ```

   - Acepta `--url-captura` para el tipo `respaldo`.
   - Valida igual que la API y muestra el token una sola vez.
   - En el PC corre con `uv run accesia crear-camara …`. El Día 3 este mismo comando suma `semilla agente`.
8. Pruebas con pytest y PostgreSQL real, cada una con su marca. Cada respuesta se valida contra su esquema con `pruebas/esquemas.py`:

   | Marca | Qué comprueba |
   | --- | --- |
   | `contrato API · <operationId>` | Cada operación de esta tarea responde con su esquema y con los códigos de error del contrato |
   | `contrato API · error` | Suma el 405 con `metodo_no_permitido` |
   | `contrato API · inscripcion_activa` | Con una inscripción activa armada en la base, `listarCamaras` y `verCamara` la muestran en `inscripcion_activa` y `modo` es `inscribir`; si ya pasó su hora, la vencen y el campo queda en `null` (R9) |
   | `RNF-02 · C2` | Cookie con `HttpOnly`, `SameSite=Strict` y `Path=/`; la clave guardada es Argon2id |
   | `RNF-02 · C5` | Cada ruta protegida responde 401 `sin_sesion` sin cookie |
   | `RF-02 · C1`, `C2` y `C5` | Personas con documento único; consentimiento con versión, medio, autor y fecha; revocación |
   | `R9 · revoca a mitad` | Con una inscripción activa y 2 huellas armadas en la base, revocar la deja `cancelada` y sin huellas |
   | `R9 · desactivar no cancela` | Desactivar a la persona deja su inscripción `activa` |
   | `RF-12 · C2` | Borrar una persona borra sus huellas, consentimientos, inscripciones y asistencia; sus eventos quedan sin persona |
   | `RF-13 · C1`, `C2` y `C3` | Horarios por bloques, reemplazo de bloques y `horario_en_uso` |
   | `RF-10 · C1`, `C2` y `C5` | Token mostrado una vez y guardado como hash, cambio de token y el comando `crear-camara` |
   | `R8 · formato` | Las fechas de la API salen en ISO 8601 con `-05:00` |

9. `servidor/README.md` (rutas, comando y marcas nuevas) y la sección «Comandos» de `CLAUDE.md` con `crear-camara`.

## No hacer

- Nada de reconocimiento, de la API de inscripciones ni de `POST …/rostros`: son de B2.
- Nada de MQTT, asistencia ni `semilla agente`: son del Día 3.
- No cambies la web: solo se regenera `esquema.d.ts`.
- Fuera de los dos cambios del contrato 1.3, no cambies contratos ni agregues campos. Si falta algo, propónlo en el PR.
- No publiques el OpenAPI de FastAPI: el contrato es `openapi.yaml`.
- No dejes claves ni tokens en el repositorio, en las pruebas ni en los registros.

## Criterios de aceptación

- C1 (contrato API 1.3) `openapi.yaml` 1.3 pasa `openapi-spec-validator` (`uvx openapi-spec-validator specs/contratos/openapi.yaml`). El 405 responde `metodo_no_permitido` y `Dispositivo` trae `inscripcion_activa`. `decisiones.md` y `contratos/README.md` lo anotan, y `npm run tipos` no deja cambios.
- C2 (RNF-02 · C2 y C5) Con `docker compose -f infra/compose.yaml up -d --build`, el administrador de `infra/.env` entra, y sin sesión todo responde 401.
- C3 (RF-02 · C1, C2 y C5; R9 · revoca a mitad) Personas y consentimiento cumplen el contrato, y revocar borra las huellas y cancela la inscripción activa en la misma transacción.
- C4 (RF-13 · C1 a C3) Los horarios por bloques funcionan con sus errores.
- C5 (RF-10 · C1, C2, C3 y C5; R9) Las cámaras se crean por la API y por `crear-camara`; el token se muestra una vez y se guarda como hash; cada cámara muestra su inscripción activa.
- C6 (RF-12 · C2) Borrar una persona cumple el contrato.
- C7 La web, con `npm run dev` y el servidor en Compose, entra y crea una persona con su consentimiento. Es una prueba a mano; la de Playwright es de C.
- C8 (RNF-06 · C3) `uv run pytest` en verde en el equipo y en `servidor.yml`, y `web.yml` en verde en el PR.
- C9 `servidor/README.md`, `CLAUDE.md`, las specs y la bitácora al día.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado por marca, y qué decidiste: nombre del administrador, duración de la sesión y lo que tomaste del simulacro.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con las etiquetas `frente-b` y `contrato`, con la aprobación de A y C para el contrato 1.3. Se fusiona con `servidor.yml` y `web.yml` en verde. Cuando esté en `main`, avisa a C (que actualiza su rama) y empieza B2.
- El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
