# Nombre: Dockerfile
# Descripción: Imagen del complemento accesia_base: PostgreSQL 18 con pgvector, más jq para leer las opciones.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Desde Supervisor 2026.04 no llega BUILD_FROM: el FROM va explícito. pgvector/pgvector:pg18 es la misma imagen del
# Compose del portátil y se publica para amd64 y arm64.
FROM pgvector/pgvector:pg18

ARG BUILD_ARCH
ARG BUILD_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/*

COPY run.sh /run.sh
# Sin el \r de Windows, por si run.sh se copió con fin de línea CRLF.
RUN sed -i 's/\r$//' /run.sh && chmod a+x /run.sh

LABEL io.hass.type="app" io.hass.arch="${BUILD_ARCH}" io.hass.version="${BUILD_VERSION}"

ENTRYPOINT ["/run.sh"]
