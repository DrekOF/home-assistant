"""
Nombre: test_recorte.py
Descripción: Pruebas de la fórmula del recorte con los casos de specs/contratos/casos-recorte.json, los mismos que usa el firmware (RF-01 · C6).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import json

import pytest
from dobles import DetectorFalso, imagen_sintetica

from simulador.imagen import decodificar_jpeg
from simulador.recortador import Envio, RecortadorYuNet
from simulador.recorte import Cara, calcular_recorte, elegir_cara
from simulador.rutas import RAIZ

CASOS_RECORTE = RAIZ / "specs" / "contratos" / "casos-recorte.json"
DATOS = json.loads(CASOS_RECORTE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "caso",
    [
        pytest.param(caso, id=caso["nombre"], marks=pytest.mark.marca(f"contrato recorte · {caso['nombre']}"))
        for caso in DATOS["casos"]
    ],
)
def test_caso_del_contrato(caso: dict) -> None:
    # La fórmula del simulador usa w/4 y h/4: si el contrato cambia el margen, esta prueba avisa.
    assert DATOS["margen"] == 0.25

    caras = [Cara(**cara) for cara in caso["caras"]]
    ancho, alto = caso["cuadro"]["ancho"], caso["cuadro"]["alto"]
    esperado = caso["esperado"]

    # cara_min = 0: aquí se prueba la elección por área; el tamaño mínimo tiene su propia prueba.
    indice = elegir_cara(caras, cara_min=0)
    assert indice == esperado["cara"]

    recorte = calcular_recorte(caras[indice], ancho, alto)
    assert (recorte.x0, recorte.y0) == (esperado["x0"], esperado["y0"])
    assert (recorte.x1, recorte.y1) == (esperado["x1"], esperado["y1"])
    assert (recorte.ancho, recorte.alto) == (esperado["ancho"], esperado["alto"])

    # Y el recortador corta justo ese rectángulo del cuadro, sin incluir x1 ni y1.
    resultado = RecortadorYuNet(DetectorFalso(caras), cara_min=0).procesar(imagen_sintetica(ancho, alto))
    assert isinstance(resultado, Envio)
    assert resultado.recorte == recorte
    assert decodificar_jpeg(resultado.jpeg).shape[:2] == (esperado["alto"], esperado["ancho"])
