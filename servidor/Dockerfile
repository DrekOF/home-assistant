# Nombre: Dockerfile
# Descripción: Imagen del servidor de AccesIA (multietapa con uv, usuario sin privilegios, amd64 y arm64), con los modelos de cara descargados y comprobados al construir.
# Fecha de creación: 2026-11-11
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.2
#
# Se construye con la raíz del repositorio como contexto: docker build -f servidor/Dockerfile .
# Las versiones exactas de las imágenes base se fijan el Día 4 (specs/arquitectura.md).

# YuNet y SFace (opencv_zoo, commit fijo) se descargan una sola vez, en la plataforma que construye: un ONNX no
# depende de la arquitectura. modelos.py solo usa la biblioteca estándar y comprueba el tamaño y el SHA-256 de cada
# modelo; si no coinciden, la construcción falla. Esta capa se reutiliza mientras modelos.py no cambie.
FROM --platform=$BUILDPLATFORM python:3.13-slim AS modelos
COPY servidor/accesia/modelos.py /tmp/modelos.py
RUN python /tmp/modelos.py --carpeta /app/datos/modelos


FROM python:3.13-slim AS construccion

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app/servidor

# Primero las dependencias, para aprovechar la caché de capas.
COPY servidor/pyproject.toml servidor/uv.lock servidor/README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY servidor/ ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.13-slim

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin accesia

WORKDIR /app/servidor
COPY --from=construccion --chown=accesia:accesia /app/servidor /app/servidor
# El SQL del contrato y el texto del consentimiento van en la misma ruta relativa que en el repositorio:
# la migración y GET /api/v1/consentimiento/texto los buscan así.
COPY specs/contratos/base-de-datos.sql /app/specs/contratos/base-de-datos.sql
COPY specs/consentimiento.md /app/specs/consentimiento.md
# Los modelos van en datos/modelos/ desde la raíz, como en el PC (accesia/modelos.py), y quedan de solo lectura.
COPY --from=modelos /app/datos/modelos /app/datos/modelos

ENV PATH="/app/servidor/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER accesia
EXPOSE 8000

# Primero las migraciones y después la API, con un solo proceso de Uvicorn (sin --workers).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn accesia.main:app --host 0.0.0.0 --port 8000"]
