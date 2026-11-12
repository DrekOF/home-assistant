"""
Nombre: test_caras_reales.py
Descripción: Pruebas con caras reales de datos/prueba/ (fotos <persona>-<n>.jpg del equipo, con su permiso): YuNet encuentra la cara, SFace da una huella normalizada y las fotos de una misma persona coinciden. Sin la carpeta, se saltan; en la CI siempre se saltan.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

from accesia.config import Configuracion
from accesia.vision import cara_mas_grande, caras_validas, decodificar_jpeg

CARPETA = Path(__file__).resolve().parents[2] / "datos" / "prueba"
FOTOS = sorted(ruta for ruta in CARPETA.glob("*") if ruta.suffix.lower() in {".jpg", ".jpeg"}) if CARPETA.is_dir() else []

pytestmark = pytest.mark.skipif(
    not FOTOS,
    reason="No hay fotos en datos/prueba/ (<persona>-<n>.jpg): las pruebas con caras reales se saltan. "
    "En la CI siempre se saltan, porque el repositorio no tiene caras.",
)


def _persona(ruta: Path) -> str:
    return ruta.stem.rsplit("-", 1)[0]


def _huella(vision_real, ruta: Path) -> np.ndarray:
    imagen = decodificar_jpeg(ruta.read_bytes())
    assert imagen is not None, f"{ruta.name} no es un JPEG que se pueda leer"
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
def test_las_fotos_de_una_misma_persona_coinciden(vision_real) -> None:
    umbral = Configuracion.model_fields["umbral_similitud"].default
    por_persona: dict[str, list[np.ndarray]] = defaultdict(list)
    for ruta in FOTOS:
        por_persona[_persona(ruta)].append(_huella(vision_real, ruta))
    parejas = [(persona, a, b) for persona, huellas in por_persona.items() for a, b in combinations(huellas, 2)]
    if not parejas:
        pytest.skip("Hace falta al menos una persona con dos fotos en datos/prueba/.")

    for persona, a, b in parejas:
        similitud = float(np.dot(a, b))
        assert similitud >= umbral, f"Dos fotos de {persona} dan {similitud:.3f}, bajo el umbral {umbral}"
