"""
Nombre: test_caras_reales.py
Descripción: Pruebas con caras reales de datos/prueba/, la misma carpeta del modo carpeta del simulador (fotos <persona>-<n>, con el permiso de quien aparece): YuNet encuentra la cara, SFace da una huella normalizada y cada foto se parece a otra de la misma persona. Sin fotos se saltan; en la CI siempre se saltan.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import pytest

from accesia.config import Configuracion
from accesia.vision import cara_mas_grande, caras_validas

CARPETA = Path(__file__).resolve().parents[2] / "datos" / "prueba"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}  # las mismas del modo carpeta del simulador
NOMBRE = re.compile(r"^(?P<persona>.+)-(?P<numero>\d+)$")  # ana-01, bruno-02…


def _fotos_con_cara() -> list[Path]:
    """Las fotos <persona>-<n> de la carpeta, sin las que esperado.json marca como no enviadas (por ejemplo, una pared)."""
    if not CARPETA.is_dir():
        return []
    no_enviadas: set[str] = set()
    esperado = CARPETA / "esperado.json"
    if esperado.is_file():
        datos = json.loads(esperado.read_text(encoding="utf-8"))
        fotos = datos.get("fotos", {}) if isinstance(datos, dict) else {}  # formato de simulador/README.md
        no_enviadas = {
            nombre for nombre, valor in fotos.items() if isinstance(valor, dict) and valor.get("enviada") is False
        }
    return sorted(
        ruta
        for ruta in CARPETA.iterdir()
        if ruta.suffix.lower() in EXTENSIONES and NOMBRE.match(ruta.stem) and ruta.name not in no_enviadas
    )


FOTOS = _fotos_con_cara()

pytestmark = pytest.mark.skipif(
    not FOTOS,
    reason="No hay fotos <persona>-<n> en datos/prueba/: las pruebas con caras reales se saltan. "
    "En la CI siempre se saltan, porque el repositorio no tiene caras.",
)


def _huella(vision_real, ruta: Path) -> np.ndarray:
    """La huella de la cara más grande de la foto, leída en memoria (la foto es del equipo y no se copia)."""
    imagen = cv2.imdecode(np.frombuffer(ruta.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert imagen is not None, f"{ruta.name} no se pudo leer"
    cara = cara_mas_grande(caras_validas(vision_real.detectar(imagen)))
    assert cara is not None, f"YuNet no encontró una cara con puntaje de 0,9 o más en {ruta.name}"
    return vision_real.huella(imagen, cara).vector


@pytest.mark.marca("RF-04 · C1")
def test_cada_foto_real_da_una_cara_y_una_huella_normalizada(vision_real) -> None:
    for ruta in FOTOS:
        vector = _huella(vision_real, ruta)
        assert vector.shape == (128,)
        assert float(np.linalg.norm(vector)) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.marca("RF-04 · C2")
def test_cada_foto_se_parece_a_otra_de_la_misma_persona(vision_real) -> None:
    """Como R2: cuenta la foto más parecida de la misma persona, que debe llegar al umbral inicial de R1."""
    umbral = Configuracion.model_fields["umbral_similitud"].default
    por_persona: dict[str, list[tuple[str, np.ndarray]]] = defaultdict(list)
    for ruta in FOTOS:
        por_persona[NOMBRE.match(ruta.stem)["persona"]].append((ruta.name, _huella(vision_real, ruta)))
    grupos = {persona: fotos for persona, fotos in por_persona.items() if len(fotos) >= 2}
    if not grupos:
        pytest.skip("Hace falta al menos una persona con dos fotos en datos/prueba/.")

    for persona, fotos in grupos.items():
        for nombre, huella in fotos:
            mejor = max(float(np.dot(huella, otra)) for otro, otra in fotos if otro != nombre)
            assert mejor >= umbral, f"{nombre} se parece a lo sumo {mejor:.3f} a otra foto de {persona} (umbral {umbral})"
