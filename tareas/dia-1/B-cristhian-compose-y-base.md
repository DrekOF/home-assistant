<!--
Nombre: B-cristhian-compose-y-base.md
Descripción: Tarea del Día 1 del frente B: Docker Compose base, esquema de la base con migraciones y esqueleto del servidor.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.2
-->

# Día 1 · Frente B · Docker Compose, base de datos y esqueleto del servidor

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/compose-y-base`
- Lee primero: `CLAUDE.md`; `specs/arquitectura.md` (Servicios y Configuración); `specs/modelo-datos.md`; `specs/contratos/base-de-datos.sql`; `specs/contratos/openapi.yaml` (solo `/api/v1/salud` y `Error`); `specs/contratos/mqtt.md` (Broker); `specs/decisiones.md` (D-04, D-14, D-15 y D-16); `specs/requisitos.md` (RNF-06 · C3).

## Objetivo

Que con un comando se levanten PostgreSQL 18 + pgvector, Mosquitto y el servidor, con el esquema del contrato migrado y `/api/v1/salud` respondiendo, que haya pruebas que lo comprueben y que GitHub Actions las corra en cada PR.

## Hacer

1. `infra/`:
   - `compose.yaml` con `postgres`, `mosquitto` y `servidor` según `arquitectura.md`: puertos, volúmenes y healthchecks; `servidor` espera a que `postgres` esté sano. `homeassistant`, `ollama` y `mcp` llegan el Día 3.
     - El volumen `datos-postgres` se monta en `/var/lib/postgresql`: PostgreSQL 18 guarda los datos en `/var/lib/postgresql/18/docker` y ya no usa `/var/lib/postgresql/data`.
     - `servidor` se construye con la raíz del repositorio como contexto (`context: ..` y `dockerfile: servidor/Dockerfile`).
   - `.env.example` con todas las variables de `arquitectura.md`, sin claves. `ADMIN_CORREO` de ejemplo con un dominio no reservado (`admin@example.com`): la validación de correos rechaza `.local`.
   - `mosquitto/mosquitto.conf` con `listener 1883` (sin él, Mosquitto 2 solo escucha dentro del contenedor), sin acceso anónimo, con archivo de claves y ACL; y `mosquitto/acl` igual al de `mqtt.md`, con las líneas `pattern` por client id.
   - `scripts/generar-env.ps1` y `.sh`: crean `infra/.env` desde el ejemplo con claves aleatorias, solo si no existe.
   - `scripts/crear-claves-mqtt.ps1` y `.sh`: generan `infra/mosquitto/claves/passwd` desde `infra/.env` con `mosquitto_passwd` dentro del contenedor.
   - Los `.ps1` van en UTF-8 con BOM, como pide `.editorconfig`: sin BOM, Windows PowerShell 5.1 lee mal las tildes.
2. `servidor/` (Python 3.13 con uv, paquete `accesia`):
   - Dependencias: FastAPI, Uvicorn, pydantic-settings, SQLAlchemy 2, psycopg 3, pgvector, Alembic y `tzdata` (para que `America/Bogota` no dependa de la imagen base). Para pruebas: pytest, httpx y testcontainers.
   - `accesia/config.py` (variables de `arquitectura.md`), `accesia/db.py`, `accesia/main.py` y `accesia/api/salud.py`.
   - Todos los errores con el esquema `Error` de `openapi.yaml` (`detalle` y `codigo`), incluidos los de validación (`codigo: validacion`).
   - Migración inicial de Alembic que ejecuta tal cual `specs/contratos/base-de-datos.sql` (versión 1.2, con los horarios por bloques de D-20) y luego crea el usuario `agente` con `AGENTE_DB_PASSWORD`. La clave va como literal escapado, nunca concatenada a mano.
   - Al arrancar, el contenedor aplica las migraciones y luego inicia la API con un solo proceso de Uvicorn (sin `--workers`): R6, el control del 429 y MQTT vivirán en memoria.
   - `GET /api/v1/salud` según `openapi.yaml`. Hasta el Día 3, `mqtt` responde `sin_conexion` y `estado` es `degradado`.
   - `Dockerfile` multietapa con uv y un usuario sin privilegios, que construya para `linux/amd64` y `linux/arm64`. Se construye con la raíz del repositorio como contexto (`docker build -f servidor/Dockerfile .`) para copiar `specs/contratos/base-de-datos.sql` y, desde el Día 2, el texto de `specs/consentimiento.md`. Un `.dockerignore` en la raíz deja fuera `datos/`, `kit/`, `node_modules/` y lo que la imagen no necesita. Los modelos ONNX se agregan el Día 2.
3. Pruebas con pytest y un PostgreSQL real (testcontainers con la imagen `pgvector/pgvector:pg18`):

   | Marca | Qué comprueba |
   | --- | --- |
   | `contrato BD · esquema` | Tras migrar, las tablas, columnas, índices y vistas son los del contrato |
   | `contrato BD · vector` | Con huellas de prueba, la búsqueda central de `modelo-datos.md` devuelve la más parecida (R2) |
   | `RF-08 · C4` | El usuario `agente` lee las tres vistas y falla al leer `persona` o `rostro` y al insertar |
   | `contrato API · salud` | `GET /api/v1/salud` responde 200 con el esquema `Salud` |
   | `contrato API · error` | Un error de validación responde con el esquema `Error` |

4. `servidor/README.md` e `infra/README.md` con cómo levantar todo y correr las pruebas, y la sección «Comandos» de `CLAUDE.md` completa. `infra/README.md` explica cómo ver si Windows reservó el puerto de `POSTGRES_PORT` (`netsh interface ipv4 show excludedportrange protocol=tcp`) y cómo cambiarlo.
5. `.github/workflows/servidor.yml`: en cada PR y en cada push a `main`, instala uv y corre `uv run pytest` en `servidor/` sobre `ubuntu-latest`, que trae Docker para testcontainers. Es solo del servidor: la web tiene su propio workflow (tarea C) y el firmware se suma el Día 4.

## No hacer

- Nada de reconocimiento, reglas ni MQTT en el servidor todavía (Días 2 y 3).
- No publiques el puerto 5432 en el PC: usa `POSTGRES_PORT`.
- No subas `infra/.env` ni ninguna clave.

## Criterios de aceptación

- C1 `docker compose -f infra/compose.yaml up -d --build` deja `postgres` sano, `mosquitto` arriba y `http://localhost:8000/api/v1/salud` respondiendo.
- C2 El esquema migrado es el del contrato (prueba en verde).
- C3 `RF-08 · C4` en verde.
- C4 Mosquitto rechaza las conexiones anónimas y acepta a los usuarios `servidor`, `homeassistant` y `camara`. Con el usuario `camara`, un cliente solo publica en los temas de su client id y no puede publicar en `accesia/servidor/disponible`.
- C5 `uv run pytest` en verde.
- C6 La bitácora y los README están al día.
- C7 (RNF-06 · C3) `servidor.yml` corre en el PR de esta tarea y queda en verde.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado, y qué decidiste.
- PR a `main` con los criterios cumplidos.
