<!--
Nombre: README.md
Descripción: Servidor de AccesIA: API, reconocimiento, reglas, MQTT y MCP (frente B).
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Servidor · frente B

Python 3.13 con FastAPI: saca la huella de la cara (YuNet + SFace), aplica las reglas, guarda en PostgreSQL con pgvector, publica en MQTT, sirve la web y, con otro comando, el servidor MCP del agente.

- Specs: `specs/arquitectura.md`, `specs/reglas.md`, `specs/modelo-datos.md` y todos los contratos.
- Lo crea la tarea `tareas/dia-1/B-cristhian-compose-y-base.md`. La tarea B1 del Día 2 suma la sesión y la API de administración; B2, el reconocimiento y la inscripción; MQTT, asistencia y MCP son del Día 3.

## Qué hay

| Ruta | Qué es |
| --- | --- |
| `accesia/config.py`, `db.py`, `tiempo.py` | Variables de `arquitectura.md`; motor de la base y una transacción por petición; hora de Colombia (R8) |
| `accesia/errores.py` y `esquemas.py` | El esquema `Error` y los esquemas de `openapi.yaml` 1.3 con pydantic |
| `accesia/sesion.py` y `seguridad.py` | Cookie de sesión firmada, primer administrador, Argon2id para las claves y SHA-256 para los tokens |
| `accesia/consentimiento.py`, `inscripciones.py` y `camaras.py` | Texto del consentimiento, vencer y cancelar inscripciones (R9) y la lógica de las cámaras que comparten la API y el comando |
| `accesia/api/` | Rutas: `salud`, `sesion`, `personas`, `consentimiento`, `horarios` y `camaras` |
| `accesia/comandos.py` | El comando `accesia` (por ahora, `crear-camara`) |
| `accesia/main.py` | La aplicación: al arrancar exige `SESION_SECRETO` y crea el primer administrador |
| `migraciones/` | Alembic. La migración `0001` ejecuta tal cual `specs/contratos/base-de-datos.sql` y crea el usuario `agente` |
| `pruebas/` | pytest con PostgreSQL 18 + pgvector y Mosquitto en contenedores (testcontainers); `armar.py` arma datos en la base |
| `Dockerfile` | Imagen multietapa con uv; se construye desde la raíz del repositorio y copia el SQL del contrato y `specs/consentimiento.md` |
| `pyproject.toml` y `uv.lock` | Dependencias, fijadas por uv |

## Requisitos

- uv: `winget install --id astral-sh.uv -e`. Después cierra y abre la terminal para que encuentre `uv`.
- Docker Desktop abierto: las pruebas levantan sus propios contenedores. Si dicen que no encuentran Docker (`CreateFile`), Docker Desktop está cerrado.

## Comandos

Desde la carpeta `servidor/`:

| Para qué | Comando |
| --- | --- |
| Instalar las dependencias, con las de pruebas | `uv sync` |
| Correr todas las pruebas | `uv run pytest` |
| Correr solo las de la ACL de MQTT | `uv run pytest -k acl` |
| Correr la API en el PC, contra la base de Compose | `$env:DATABASE_URL = "postgresql+psycopg://accesia:<clave>@127.0.0.1:5434/accesia"` y `$env:SESION_SECRETO = "<de infra/.env>"`, y luego `uv run uvicorn accesia.main:app --reload` |
| Aplicar las migraciones a mano | con `DATABASE_URL` y `AGENTE_DB_PASSWORD` en el entorno, `uv run alembic upgrade head` |
| Registrar una cámara en el PC | con `DATABASE_URL` en el entorno, `uv run accesia crear-camara entrada --nombre Entrada --tipo simulador` |

La clave de PostgreSQL es `POSTGRES_PASSWORD` de `infra/.env`. En el contenedor no hace falta nada de esto: al arrancar aplica las migraciones y luego inicia Uvicorn con un solo proceso.

## Comando `crear-camara`

Registra una cámara sin pasar por la web (RF-10 · C5) y muestra su token una sola vez; la base guarda solo su SHA-256. Valida igual que `POST /api/v1/dispositivos`. Con Compose arriba, desde la raíz del repositorio:

```powershell
docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador
```

- `--tipo` es `tinyml`, `respaldo` o `simulador`; el tipo `respaldo` pide `--url-captura`.
- El código `servidor` está reservado. Si el código ya existe, no cambia nada y lo dice: el token se cambia desde la web o con `POST /api/v1/dispositivos/{codigo}/token`.
- La última línea que imprime es solo el token, para copiarlo sin errores.

## Sesión y primer administrador

- `POST /api/v1/sesion` deja la cookie `accesia_sesion`: firmada con `SESION_SECRETO`, `HttpOnly`, `SameSite=Strict` y `Path=/`. Solo guarda el id del administrador.
- La sesión dura 8 horas desde el último uso: cada respuesta con sesión renueva la cookie. Si el administrador se desactiva, su sesión deja de servir en la siguiente petición.
- Al arrancar, si no existe un administrador con `ADMIN_CORREO`, el servidor lo crea con `ADMIN_CLAVE_INICIAL` y el nombre «Administrador». Si ya existe, no toca su clave. Sin `SESION_SECRETO`, el servidor no arranca.
- Las claves se guardan con Argon2id. Un correo que no existe, una clave equivocada o un administrador inactivo responden lo mismo: 401 `credenciales_invalidas`.

## Rutas

Todas piden sesión (401 `sin_sesion` sin ella), menos `GET /api/v1/salud` y `POST /api/v1/sesion`. `DELETE /api/v1/sesion` responde 204 haya sesión o no.

| Rutas | Operaciones de `openapi.yaml` |
| --- | --- |
| `/api/v1/sesion` | `iniciarSesion`, `verSesion`, `cerrarSesion` |
| `/api/v1/personas` y `/api/v1/personas/{persona_id}` | `listarPersonas`, `crearPersona`, `verPersona`, `editarPersona`, `borrarPersona` |
| `/api/v1/consentimiento/texto`, `/api/v1/personas/{persona_id}/consentimiento` y `…/consentimientos` | `verTextoConsentimiento`, `verConsentimiento`, `registrarConsentimiento`, `revocarConsentimiento`, `listarConsentimientos` |
| `/api/v1/horarios` y `/api/v1/horarios/{horario_id}` | `listarHorarios`, `crearHorario`, `editarHorario`, `borrarHorario` |
| `/api/v1/dispositivos`, `/api/v1/dispositivos/{codigo}` y `…/token` | `listarCamaras`, `crearCamara`, `verCamara`, `editarCamara`, `cambiarTokenCamara` |

Donde el contrato no dice nada, la API responde como el simulacro de la web: personas ordenadas por nombre con la colación española, un horario que no existe es 422 `validacion`, un `PATCH` vacío también, y un id que no es un uuid es 404. Una ruta que existe, llamada con otro método, responde 405 `metodo_no_permitido` (contrato 1.3).

## Pruebas

Cada prueba lleva su marca (`@pytest.mark.marca("…")`) y pytest no corre si alguna no la tiene. Al final, pytest muestra cuántas pasaron por marca.

Las pruebas de la API usan la conexión de la prueba, dentro de una transacción que se deshace al final. Cada petición corre en su savepoint, como una transacción del servidor real, y las consultas que pueden chocar con una restricción abren otro: así, después de un 409, la prueba sigue sin que PostgreSQL deje la transacción abortada.

| Marca | Qué comprueba |
| --- | --- |
| `contrato BD · esquema` | La base migrada tiene las mismas tablas, columnas, restricciones, índices, vistas y permisos que el contrato cargado aparte |
| `contrato BD · vector` | La búsqueda central de `modelo-datos.md` devuelve la muestra más parecida (R2) |
| `contrato BD · horarios` | Horarios por bloques (D-20): cinco bloques en «Clase IA», un bloque por día, borrado en cascada, `restrict_violation` (23001) al borrar uno en uso y días de la vista del agente |
| `RF-08 · C4` | El usuario `agente` lee sus tres vistas y no puede leer `persona`, `rostro` ni `horario_bloque`, ni insertar |
| `contrato API · salud` | `GET /api/v1/salud` cumple el esquema `Salud` y da la hora con `-05:00` |
| `contrato API · error` | Validación, ruta inexistente, método no permitido (405 con `Allow`) y error interno responden con el esquema `Error` |
| `contrato API · <operationId>` | Cada operación de sesión, personas, consentimiento, horarios y cámaras responde con su esquema y con los códigos de error del contrato |
| `contrato API · inscripcion_activa` | Una cámara muestra su inscripción activa y `modo: inscribir`; si ya pasó su hora, la vence y el campo queda en `null` (R9) |
| `RNF-02 · C2` | Cookie `HttpOnly`, `SameSite=Strict`, `Path=/` y de 8 horas; primer administrador con Argon2id; sin `SESION_SECRETO` no arranca |
| `RNF-02 · C5` | Cada ruta con sesión responde 401 `sin_sesion` sin cookie, con una firma falsa, con una cookie vencida o con el administrador desactivado |
| `RF-02 · C1`, `C2` y `C5` | Documento único, activar y desactivar; consentimiento con versión, medio, autor y fecha; revocar borra las huellas |
| `RF-10 · C1`, `C2`, `C3` y `C5` | Token mostrado una vez y guardado como SHA-256, cambio de token, en línea por el último contacto y el comando `crear-camara` |
| `RF-12 · C2` | Borrar una persona borra lo suyo y deja sus eventos sin persona |
| `RF-13 · C1`, `C2` y `C3` | Horarios por bloques, reemplazo de bloques y `horario_en_uso` |
| `R8 · formato` | Las fechas de la API salen en ISO 8601 con `-05:00` |
| `R9 · revoca a mitad` y `R9 · desactivar no cancela` | Revocar cancela la inscripción activa y borra sus huellas; desactivar a la persona no la cancela |
| `contrato MQTT · acl` | Mosquitto con el `mosquitto.conf` y la ACL del repositorio: rechaza la conexión anónima, deja entrar a los tres usuarios, y la cámara solo publica en los temas de su client id, nunca en `accesia/servidor/…` |

La CI corre `uv run pytest` en cada PR y en cada push a `main` (`.github/workflows/servidor.yml`).
