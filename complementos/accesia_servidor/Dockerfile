# Nombre: Dockerfile
# Descripción: Imagen del complemento accesia_servidor: el servidor de AccesIA con la web compilada y los modelos de cara, como la de servidor/Dockerfile, desde lo que arma scripts/empaquetar-complementos.ps1.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Supervisor solo ve la carpeta del complemento: por eso el empaquetado copia aquí servidor/, specs/, web/dist y
# datos/modelos. Desde Supervisor 2026.04 no llega BUILD_FROM: el FROM va explícito. python:3.13-slim y la imagen de
# uv se publican para amd64 y arm64; construir en la Pi baja la imagen base y los paquetes de Python (D-22).
FROM python:3.13-slim AS construccion
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app/servidor
COPY servidor/pyproject.toml servidor/uv.lock servidor/README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY servidor/ ./
RUN uv sync --locked --no-dev

FROM python:3.13-slim
ARG BUILD_ARCH
ARG BUILD_VERSION
# jq lee las opciones. El servidor corre con el usuario accesia, como en el Compose; el MCP, con el usuario agente,
# sin las claves del dueño de la base (D-15).
RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin accesia \
    && useradd --system --uid 10002 --home-dir /app --shell /usr/sbin/nologin agente
WORKDIR /app/servidor
COPY --from=construccion --chown=accesia:accesia /app/servidor /app/servidor
COPY specs/ /app/specs/
COPY datos/modelos /app/datos/modelos
COPY web/dist /app/web/dist
COPY run.sh /run.sh
# Sin el \r de Windows, por si run.sh se copió con fin de línea CRLF.
RUN sed -i 's/\r$//' /run.sh && chmod a+x /run.sh
ENV PATH="/app/servidor/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
LABEL io.hass.type="app" io.hass.arch="${BUILD_ARCH}" io.hass.version="${BUILD_VERSION}"
CMD ["/run.sh"]
