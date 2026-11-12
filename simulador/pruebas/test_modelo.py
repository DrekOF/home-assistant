"""
Nombre: test_modelo.py
Descripción: Pruebas del modelo YuNet sin red: se comprueba con su SHA-256, se descarga solo si falta o no coincide y la URL y el hash son los de specs/arquitectura.md (RNF-04 · C3).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import hashlib
from pathlib import Path

import httpx
import pytest

from simulador.modelo import (
    OPENCV_ZOO_COMMIT,
    YUNET_ARCHIVO,
    YUNET_SHA256,
    YUNET_URL,
    ErrorModelo,
    asegurar_modelo,
)
from simulador.rutas import RAIZ

pytestmark = pytest.mark.marca("RNF-04 · C3 · modelo")

CONTENIDO = b"modelo de mentira"
HASH = hashlib.sha256(CONTENIDO).hexdigest()


class DescargaFalsa:
    def __init__(self, contenido: bytes = CONTENIDO, error: Exception | None = None) -> None:
        self.contenido = contenido
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str, destino: Path) -> None:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        destino.write_bytes(self.contenido)


def _asegurar(carpeta: Path, descarga: DescargaFalsa) -> Path:
    return asegurar_modelo(carpeta, url="https://modelo.prueba/yunet.onnx", sha256=HASH, archivo="yunet.onnx",
                           descargar=descarga, avisar=lambda _: None)


def test_con_el_modelo_ya_descargado_no_usa_la_red(tmp_path: Path) -> None:
    (tmp_path / "yunet.onnx").write_bytes(CONTENIDO)
    descarga = DescargaFalsa(error=AssertionError("no debía descargar"))
    assert _asegurar(tmp_path, descarga) == tmp_path / "yunet.onnx"
    assert descarga.urls == []


def test_si_falta_lo_descarga_y_lo_comprueba(tmp_path: Path) -> None:
    descarga = DescargaFalsa()
    ruta = _asegurar(tmp_path / "modelos", descarga)
    assert ruta.read_bytes() == CONTENIDO
    assert descarga.urls == ["https://modelo.prueba/yunet.onnx"]
    assert sorted(p.name for p in ruta.parent.iterdir()) == ["yunet.onnx"]  # sin el .parcial


def test_si_no_coincide_lo_descarga_otra_vez(tmp_path: Path) -> None:
    (tmp_path / "yunet.onnx").write_bytes(b"version https://git-lfs.github.com/spec/v1")  # el puntero de LFS
    descarga = DescargaFalsa()
    assert _asegurar(tmp_path, descarga).read_bytes() == CONTENIDO
    assert len(descarga.urls) == 1


def test_descarga_con_otro_hash_no_queda_guardada(tmp_path: Path) -> None:
    with pytest.raises(ErrorModelo, match="no coincide con su SHA-256"):
        _asegurar(tmp_path, DescargaFalsa(contenido=b"otro archivo"))
    assert list(tmp_path.iterdir()) == []


def test_sin_internet_lo_dice(tmp_path: Path) -> None:
    with pytest.raises(ErrorModelo, match="Sin internet"):
        _asegurar(tmp_path, DescargaFalsa(error=httpx.ConnectError("sin red")))
    assert list(tmp_path.iterdir()) == []


def test_url_y_hash_son_los_de_arquitectura() -> None:
    """El simulador y el servidor usan el mismo archivo, de la misma URL y con el mismo SHA-256."""
    url = f"https://github.com/opencv/opencv_zoo/raw/{OPENCV_ZOO_COMMIT}/models/face_detection_yunet/{YUNET_ARCHIVO}"
    assert url == YUNET_URL
    arquitectura = (RAIZ / "specs" / "arquitectura.md").read_text(encoding="utf-8")
    assert OPENCV_ZOO_COMMIT in arquitectura
    assert YUNET_SHA256 in arquitectura
