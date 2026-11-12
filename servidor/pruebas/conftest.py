"""
Nombre: conftest.py
Descripción: Fixtures de las pruebas del servidor de AccesIA: PostgreSQL 18 + pgvector con testcontainers, la API con sesión dentro de la transacción de cada prueba, y marcas de las specs.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

import os
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from testcontainers.community.postgres import PostgresContainer

SERVIDOR = Path(__file__).resolve().parents[1]
IMAGEN_POSTGRES = "pgvector/pgvector:pg18"
CLAVE_AGENTE = "clave-agente-de-prueba"

# La sesión de la web firma su cookie con SESION_SECRETO; en las pruebas basta un valor fijo.
os.environ.setdefault("SESION_SECRETO", "secreto-de-sesion-solo-para-las-pruebas")

# --- Marcas: cada prueba dice qué spec o contrato comprueba (CLAUDE.md) ---

_marca_de: dict[str, str] = {}
_resultados: dict[str, Counter] = defaultdict(Counter)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    sin_marca = []
    for item in items:
        marca = item.get_closest_marker("marca")
        if marca is None or not marca.args:
            sin_marca.append(item.nodeid)
        else:
            _marca_de[item.nodeid] = marca.args[0]
    if sin_marca:
        raise pytest.UsageError("Cada prueba lleva su marca (CLAUDE.md). Faltan en: " + ", ".join(sin_marca))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    marca = _marca_de.get(report.nodeid)
    if marca is None:
        return
    if report.when == "call" or (report.when == "setup" and not report.passed):
        _resultados[marca][report.outcome] += 1


def pytest_terminal_summary(terminalreporter) -> None:
    if not _resultados:
        return
    terminalreporter.section("Marcas de las specs")
    for marca in sorted(_resultados):
        conteo = _resultados[marca]
        partes = [f"{conteo[resultado]} {nombre}" for resultado, nombre in
                  (("passed", "bien"), ("failed", "con falla"), ("skipped", "saltadas")) if conteo[resultado]]
        terminalreporter.write_line(f"{marca}: {', '.join(partes)}")


# --- Base de datos ---

@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        IMAGEN_POSTGRES, username="accesia", password="clave-de-prueba", dbname="accesia", driver="psycopg"
    ) as contenedor:
        yield contenedor


@pytest.fixture(scope="session")
def url_base(postgres: PostgresContainer) -> str:
    """URL de la base ya migrada con Alembic, como lo hace el contenedor del servidor."""
    url = postgres.get_connection_url()
    os.environ["DATABASE_URL"] = url
    os.environ["AGENTE_DB_PASSWORD"] = CLAVE_AGENTE

    from accesia.config import configuracion
    from accesia.db import motor

    configuracion.cache_clear()
    motor.cache_clear()

    alembic = Config(str(SERVIDOR / "alembic.ini"))
    alembic.attributes["url"] = url
    alembic.attributes["configurar_registro"] = False
    command.upgrade(alembic, "head")
    return url


@pytest.fixture(scope="session")
def motor(url_base: str) -> Iterator[Engine]:
    motor = create_engine(url_base)
    yield motor
    motor.dispose()


@pytest.fixture
def conexion(motor: Engine) -> Iterator[Connection]:
    """Conexión del dueño de la base, con una transacción que se deshace al terminar la prueba."""
    with motor.connect() as conexion:
        transaccion = conexion.begin()
        try:
            yield conexion
        finally:
            transaccion.rollback()


@pytest.fixture
def conexion_agente(url_base: str) -> Iterator[Connection]:
    """Conexión con el usuario agente, de solo lectura (D-15)."""
    motor = create_engine(make_url(url_base).set(username="agente", password=CLAVE_AGENTE))
    try:
        with motor.connect() as conexion:
            yield conexion
    finally:
        motor.dispose()


# --- API con sesión ---

CORREO_ADMIN = "admin@example.com"
CLAVE_ADMIN = "clave-de-prueba-123"
NOMBRE_ADMIN = "Administrador de prueba"


@pytest.fixture
def app(conexion: Connection) -> FastAPI:
    """La API usando la conexión de la prueba: al final se deshace todo lo que escribió.

    Cada petición corre en su propio savepoint, como una transacción del servidor real: si la petición falla
    (por ejemplo, un 409 por un documento repetido), se deshace solo lo suyo y la prueba puede seguir.
    """
    from accesia.db import obtener_conexion
    from accesia.main import crear_app

    aplicacion = crear_app()

    def conexion_de_la_peticion() -> Iterator[Connection]:
        with conexion.begin_nested():
            yield conexion

    aplicacion.dependency_overrides[obtener_conexion] = conexion_de_la_peticion
    return aplicacion


@pytest.fixture
def cliente(app: FastAPI) -> TestClient:
    """Cliente sin sesión. No corre el arranque de la app (el primer administrador se prueba aparte)."""
    return TestClient(app)


@pytest.fixture(scope="session")
def hash_admin() -> str:
    from accesia.seguridad import hash_de_clave

    return hash_de_clave(CLAVE_ADMIN)


@pytest.fixture
def administrador(conexion: Connection, hash_admin: str) -> dict:
    """Un administrador activo, dentro de la transacción de la prueba."""
    administrador_id = conexion.execute(
        text("INSERT INTO administrador (correo, clave_hash, nombre) VALUES (:correo, :hash, :nombre) RETURNING id"),
        {"correo": CORREO_ADMIN, "hash": hash_admin, "nombre": NOMBRE_ADMIN},
    ).scalar_one()
    return {"id": administrador_id, "correo": CORREO_ADMIN, "clave": CLAVE_ADMIN, "nombre": NOMBRE_ADMIN}


@pytest.fixture
def sesion(cliente: TestClient, administrador: dict) -> TestClient:
    """Cliente con la sesión del administrador de prueba iniciada."""
    respuesta = cliente.post("/api/v1/sesion", json={"correo": administrador["correo"], "clave": administrador["clave"]})
    assert respuesta.status_code == 200, respuesta.text
    return cliente
