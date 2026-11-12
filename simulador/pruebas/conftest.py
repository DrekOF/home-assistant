"""
Nombre: conftest.py
Descripción: Fixtures de las pruebas del simulador (servidor, reloj, modelo y fotos reales) y las marcas de las specs con su resumen, como en el servidor.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from collections import Counter, defaultdict
from pathlib import Path

import pytest
from dobles import RelojFalso, ServidorFalso

from simulador.carpeta import fotos_de
from simulador.modelo import YUNET_ARCHIVO, YUNET_SHA256, sha256_de
from simulador.rutas import MODELOS, PRUEBA

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
        partes = [
            f"{conteo[resultado]} {nombre}"
            for resultado, nombre in (("passed", "bien"), ("failed", "con falla"), ("skipped", "saltadas"))
            if conteo[resultado]
        ]
        terminalreporter.write_line(f"{marca}: {', '.join(partes)}")


# --- Dobles ---


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()


@pytest.fixture
def servidor() -> ServidorFalso:
    return ServidorFalso()


# --- Lo que vive en datos/ (Git lo ignora): el modelo y las fotos de prueba del equipo ---


@pytest.fixture(scope="session")
def modelo_yunet() -> Path:
    ruta = MODELOS / YUNET_ARCHIVO
    if not ruta.exists():
        pytest.skip(f"Falta {ruta}: se descarga con «uv run simulador modelo»")
    assert sha256_de(ruta) == YUNET_SHA256, f"{ruta} no coincide con su SHA-256"
    return ruta


@pytest.fixture(scope="session")
def fotos_reales() -> list[Path]:
    if not PRUEBA.is_dir():
        pytest.skip(f"No existe {PRUEBA}: las fotos de prueba del equipo viven ahí y nunca se suben")
    fotos = fotos_de(PRUEBA)
    if not fotos:
        pytest.skip(f"{PRUEBA} no tiene fotos")
    return fotos
