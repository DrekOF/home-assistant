"""
Nombre: test_modelos.py
Descripción: Pruebas de los modelos de cara: un archivo o una descarga que no coincide con su tamaño o su SHA-256 no se acepta ni queda en la carpeta, y los modelos de datos/modelos/ son los fijados. La imagen usa la misma comprobación al construir.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import hashlib
import io
from pathlib import Path

import pytest

from accesia import modelos


def _sin_avisos(_: str) -> None:
    pass


@pytest.mark.marca("modelos · SHA-256")
def test_un_archivo_que_falta_pesa_otra_cosa_o_tiene_otro_hash_no_pasa(tmp_path: Path) -> None:
    modelo = modelos.Modelo("m.onnx", "https://ejemplo.invalid/m.onnx", hashlib.sha256(b"bien").hexdigest(), 4)
    ruta = tmp_path / "m.onnx"

    assert "falta" in modelos.problema_de(ruta, modelo)
    ruta.write_bytes(b"mal")
    assert "pesa 3 bytes" in modelos.problema_de(ruta, modelo)
    ruta.write_bytes(b"malo")
    assert "SHA-256" in modelos.problema_de(ruta, modelo)
    ruta.write_bytes(b"bien")
    assert modelos.problema_de(ruta, modelo) is None


@pytest.mark.marca("modelos · SHA-256")
def test_una_descarga_que_no_coincide_se_descarta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    contenido = b"esto no es el modelo"
    falso = modelos.Modelo("m.onnx", "https://ejemplo.invalid/m.onnx", hashlib.sha256(b"otro").hexdigest(), len(contenido))
    monkeypatch.setattr(modelos, "MODELOS", (falso,))
    monkeypatch.setattr(modelos.urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(contenido))

    with pytest.raises(RuntimeError, match="no sirve"):
        modelos.descargar(tmp_path, avisar=_sin_avisos)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.marca("modelos · SHA-256")
def test_una_descarga_que_coincide_queda_y_no_se_repite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    contenido = b"modelo de prueba"
    bueno = modelos.Modelo("m.onnx", "https://ejemplo.invalid/m.onnx", hashlib.sha256(contenido).hexdigest(), len(contenido))
    descargas = []

    def abrir(*_a, **_k):
        descargas.append(1)
        return io.BytesIO(contenido)

    monkeypatch.setattr(modelos, "MODELOS", (bueno,))
    monkeypatch.setattr(modelos.urllib.request, "urlopen", abrir)

    modelos.descargar(tmp_path, avisar=_sin_avisos)
    modelos.descargar(tmp_path, avisar=_sin_avisos)

    assert (tmp_path / "m.onnx").read_bytes() == contenido
    assert len(descargas) == 1


@pytest.mark.marca("modelos · SHA-256")
def test_los_modelos_de_la_carpeta_son_los_fijados(vision_real) -> None:
    assert modelos.COMMIT == "48b10fa505aeb51fbd127fc60a5c660040e823b7"
    for modelo in modelos.MODELOS:
        assert modelos.problema_de(modelos.carpeta_modelos() / modelo.archivo, modelo) is None
