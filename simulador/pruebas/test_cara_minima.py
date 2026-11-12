"""
Nombre: test_cara_minima.py
Descripción: Pruebas de RF-01 · C3 en el simulador: no envía nada sin cara ni con caras de menos de cara_min píxeles de alto, en los dos modos.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import re
from pathlib import Path

import pytest
from dobles import CapturaFalsa, DetectorFalso, ServidorFalso, VentanaFalsa, escribir_foto, imagen_sintetica

from simulador.carpeta import correr_carpeta
from simulador.recortador import CARA_MIN, Envio, RecortadorYuNet, SinEnvio
from simulador.recorte import Cara
from simulador.ritmo import Ritmo
from simulador.rutas import RAIZ
from simulador.webcam import correr_webcam

pytestmark = pytest.mark.marca("RF-01 · C6 · cara mínima")

CUADRO = imagen_sintetica(640, 480)


def test_sin_cara_no_hay_envio() -> None:
    resultado = RecortadorYuNet(DetectorFalso([])).procesar(CUADRO)
    assert isinstance(resultado, SinEnvio)
    assert resultado.motivo == "sin_cara"


@pytest.mark.parametrize(("alto", "se_envia"), [(79, False), (79.9, False), (80, True), (120, True)])
def test_cara_min_es_el_alto_de_la_caja(alto: float, se_envia: bool) -> None:
    cara = Cara(200, 100, alto * 0.8, alto, 0.95)
    resultado = RecortadorYuNet(DetectorFalso([cara]), cara_min=80).procesar(CUADRO)
    assert isinstance(resultado, Envio) is se_envia
    if not se_envia:
        assert resultado.motivo == "cara_pequena"


def test_descarta_las_pequenas_y_elige_la_mayor_de_las_demas() -> None:
    pequena = Cara(10, 10, 60, 70, 0.99)
    grande = Cara(300, 100, 90, 110, 0.91)
    mediana = Cara(100, 200, 70, 85, 0.97)
    resultado = RecortadorYuNet(DetectorFalso([pequena, mediana, grande]), cara_min=80).procesar(CUADRO)
    assert isinstance(resultado, Envio)
    assert resultado.caja == grande
    assert resultado.puntaje == 0.91


def test_por_defecto_es_igual_a_cara_min_px() -> None:
    ejemplo = (RAIZ / "infra" / ".env.example").read_text(encoding="utf-8")
    assert int(re.search(r"^CARA_MIN_PX=(\d+)", ejemplo, re.MULTILINE).group(1)) == CARA_MIN == 80


def test_modo_carpeta_no_envia_sin_cara_ni_con_cara_pequena(tmp_path: Path, servidor: ServidorFalso) -> None:
    for nombre in ("1-sin-cara.jpg", "2-pequena.jpg", "3-buena.jpg"):
        escribir_foto(tmp_path / nombre, CUADRO)
    detector = DetectorFalso(por_llamada=[[], [Cara(100, 100, 50, 60)], [Cara(100, 100, 90, 110)]])
    lineas: list[str] = []

    codigo = correr_carpeta(
        tmp_path, RecortadorYuNet(detector), servidor.cliente(), Ritmo(),
        modo_camara=False, dormir=lambda _: None, salida=lineas.append,
    )

    assert codigo == 0
    assert len(servidor.peticiones) == 1
    assert any("1-sin-cara.jpg: no se envía, sin cara" in linea for linea in lineas)
    assert any("2-pequena.jpg: no se envía, cara pequeña" in linea for linea in lineas)


def test_modo_webcam_no_envia_sin_cara(servidor: ServidorFalso) -> None:
    captura = CapturaFalsa([CUADRO] * 5)
    codigo = correr_webcam(
        RecortadorYuNet(DetectorFalso([Cara(10, 10, 40, 50)])), servidor.cliente(), Ritmo(),
        modo_camara=False, abrir=lambda _: captura, crear_ventana=lambda: VentanaFalsa(5), salida=lambda _: None,
    )
    assert codigo == 0
    assert servidor.peticiones == []
