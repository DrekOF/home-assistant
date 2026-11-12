"""
Nombre: test_como_camara.py
Descripción: Pruebas del modo «como la cámara» (RNF-07): deja la imagen en 320 × 240 sin deformarla y la pasa por JPEG 80 antes de detectar, en los dos modos.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path

import cv2
import numpy as np
import pytest
from dobles import CapturaFalsa, DetectorFalso, ServidorFalso, VentanaFalsa, escribir_foto, ruido

from simulador.carpeta import correr_carpeta
from simulador.imagen import como_camara, recortar_a_4_3
from simulador.recortador import RecortadorYuNet
from simulador.recorte import Cara
from simulador.ritmo import Ritmo
from simulador.webcam import correr_webcam

pytestmark = pytest.mark.marca("RNF-07 · como la cámara")


def _circulo(ancho: int, alto: int) -> tuple[np.ndarray, int]:
    imagen = np.zeros((alto, ancho, 3), np.uint8)
    radio = min(ancho, alto) // 4
    cv2.circle(imagen, (ancho // 2, alto // 2), radio, (255, 255, 255), -1)
    return imagen, radio


def _caja_blanca(imagen: np.ndarray) -> tuple[float, float, int, int]:
    """Centro, ancho y alto de lo blanco."""
    filas, columnas = np.nonzero(imagen[:, :, 0] > 127)
    ancho = int(columnas.max() - columnas.min() + 1)
    alto = int(filas.max() - filas.min() + 1)
    return (columnas.min() + columnas.max()) / 2, (filas.min() + filas.max()) / 2, ancho, alto


@pytest.mark.parametrize(
    ("ancho", "alto"),
    [(1280, 720), (1920, 1080), (1366, 768), (640, 480), (320, 240), (720, 1280)],
    ids=["16:9 HD", "16:9 Full HD", "1366 x 768", "4:3", "ya es 320 x 240", "vertical"],
)
def test_queda_en_320_x_240_sin_deformar(ancho: int, alto: int) -> None:
    imagen, radio = _circulo(ancho, alto)
    salida = como_camara(imagen)

    assert salida.shape == (240, 320, 3)
    centro_x, centro_y, ancho_circulo, alto_circulo = _caja_blanca(salida)
    # Sigue siendo un círculo: reducir 16:9 a 320 × 240 sin recortar lo dejaría un 33 % más angosto.
    assert abs(ancho_circulo - alto_circulo) <= 2
    assert abs(centro_x - 159.5) <= 1.5 and abs(centro_y - 119.5) <= 1.5
    # La escala es la misma en los dos ejes: la del 4:3 del centro a 320 × 240.
    alto_4_3 = recortar_a_4_3(imagen).shape[0]
    assert abs(alto_circulo - 2 * radio * 240 / alto_4_3) <= 3


def test_16_9_pierde_los_lados_y_no_la_altura() -> None:
    assert recortar_a_4_3(np.zeros((720, 1280, 3), np.uint8)).shape[:2] == (720, 960)
    assert recortar_a_4_3(np.zeros((1280, 720, 3), np.uint8)).shape[:2] == (540, 720)
    assert recortar_a_4_3(np.zeros((480, 640, 3), np.uint8)).shape[:2] == (480, 640)


def test_pasa_por_jpeg_80(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[list[int]] = []
    imencode = cv2.imencode

    def espia(extension: str, imagen: np.ndarray, parametros: list[int]) -> tuple[bool, np.ndarray]:
        llamadas.append(list(parametros))
        return imencode(extension, imagen, parametros)

    monkeypatch.setattr(cv2, "imencode", espia)
    imagen = ruido(1280, 720)
    salida = como_camara(imagen)

    assert llamadas == [[cv2.IMWRITE_JPEG_QUALITY, 80]]
    sin_jpeg = cv2.resize(recortar_a_4_3(imagen), (320, 240), interpolation=cv2.INTER_AREA)
    assert not np.array_equal(salida, sin_jpeg)  # el JPEG cambió los píxeles: sí pasó por él


def test_carpeta_detecta_sobre_la_imagen_reducida(tmp_path: Path, servidor: ServidorFalso) -> None:
    escribir_foto(tmp_path / "hd.png", _circulo(1280, 720)[0])
    for modo_camara, forma in ((True, (240, 320, 3)), (False, (720, 1280, 3))):
        detector = DetectorFalso([Cara(120, 60, 80, 100)])
        codigo = correr_carpeta(
            tmp_path, RecortadorYuNet(detector), servidor.cliente(), Ritmo(), modo_camara=modo_camara,
            dormir=lambda _: None, salida=lambda _: None,
        )
        assert codigo == 0
        assert detector.formas == [forma]


def test_webcam_detecta_sobre_la_imagen_reducida(servidor: ServidorFalso) -> None:
    detector = DetectorFalso([Cara(120, 60, 80, 100)])
    ventana = VentanaFalsa(3)
    codigo = correr_webcam(
        RecortadorYuNet(detector), servidor.cliente(), Ritmo(), modo_camara=True,
        abrir=lambda _: CapturaFalsa([_circulo(1280, 720)[0]] * 3), crear_ventana=lambda: ventana,
        salida=lambda _: None,
    )
    assert codigo == 0
    assert detector.formas == [(240, 320, 3)] * 3
    assert ventana.formas == [(480, 640, 3)] * 3  # la ventana la muestra al doble
    assert len(servidor.peticiones) == 1
