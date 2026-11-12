"""
Nombre: test_yunet.py
Descripción: Pruebas con el YuNet real (RF-01 · C6): sin caras no detecta nada, y con las fotos de datos/prueba/ cada recorte cumple el contrato. Se saltan si falta el modelo o las fotos.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path

import numpy as np
import pytest
from dobles import imagen_sintetica

from simulador.deteccion import DetectorYuNet
from simulador.imagen import leer_foto, preparar
from simulador.recortador import LIMITE_BYTES, Envio, RecortadorYuNet


@pytest.mark.marca("RF-01 · C6 · YuNet")
@pytest.mark.parametrize(("ancho", "alto"), [(320, 240), (640, 480), (1280, 720)])
def test_sin_caras_no_detecta_nada(modelo_yunet: Path, ancho: int, alto: int) -> None:
    detector = DetectorYuNet(modelo_yunet)
    assert detector.detectar(np.zeros((alto, ancho, 3), np.uint8)) == []
    assert detector.detectar(imagen_sintetica(ancho, alto)) == []


@pytest.mark.marca("RF-01 · C6 · fotos reales")
@pytest.mark.parametrize("modo_camara", [False, True], ids=["normal", "como la cámara"])
def test_fotos_reales(modelo_yunet: Path, fotos_reales: list[Path], modo_camara: bool) -> None:
    """Con las fotos del equipo, cada recorte cabe en el cuadro, pesa 100 000 bytes o menos y trae un puntaje de 0 a 1.

    Lo que responde el servidor a cada foto lo compara el modo carpeta con esperado.json. Nada se guarda.
    """
    recortador = RecortadorYuNet(DetectorYuNet(modelo_yunet))
    for foto in fotos_reales:
        imagen = leer_foto(foto)
        assert imagen is not None, f"no se pudo leer {foto.name}"
        preparada = preparar(imagen, modo_camara)
        resultado = recortador.procesar(preparada)
        if not isinstance(resultado, Envio):
            continue
        alto, ancho = preparada.shape[:2]
        assert 0 <= resultado.recorte.x0 < resultado.recorte.x1 <= ancho, foto.name
        assert 0 <= resultado.recorte.y0 < resultado.recorte.y1 <= alto, foto.name
        assert len(resultado.jpeg) <= LIMITE_BYTES, foto.name
        assert 0 <= resultado.puntaje <= 1, foto.name
