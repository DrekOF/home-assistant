"""
Nombre: test_vision.py
Descripción: Pruebas de la visión y del registro: RF-04 · C1 con SFace real, la fórmula del recorte (contrato recorte), RNF-01 · C1 (la imagen solo vive en memoria) y los avisos INFO en el registro del proceso.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import base64
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import armar
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from vision_falsa import CaraArmada, VisionFalsa, eje

from accesia.vision import Cara, caja_del_recorte, cara_mas_grande, decodificar_jpeg, recortar_cara_mas_grande

RAIZ = Path(__file__).resolve().parents[2]
CASOS = json.loads((RAIZ / "specs" / "contratos" / "casos-recorte.json").read_text(encoding="utf-8"))["casos"]


# --- RF-04 · C1: la huella ---


@pytest.mark.marca("RF-04 · C1")
def test_sface_real_da_128_numeros_con_norma_1(vision_real) -> None:
    alineada = np.random.default_rng(7).integers(0, 256, (112, 112, 3), dtype=np.uint8)  # 112 × 112 sin cara

    vector = vision_real.huella_de_alineada(alineada)

    assert vector.shape == (128,)
    assert vector.dtype == np.float32
    assert float(np.linalg.norm(vector)) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.marca("RF-04 · C1")
def test_alinear_y_sacar_la_huella_de_una_cara_detectada(vision_real) -> None:
    imagen = np.random.default_rng(8).integers(0, 256, (150, 120, 3), dtype=np.uint8)
    puntos = (40.0, 60.0, 80.0, 60.0, 60.0, 80.0, 45.0, 100.0, 75.0, 100.0)
    cara = Cara(x=15, y=25, ancho=90, alto=110, puntaje=0.95, puntos=puntos)

    huella = vision_real.huella(imagen, cara)

    assert huella.vector.shape == (128,)
    assert float(np.linalg.norm(huella.vector)) == pytest.approx(1.0, abs=1e-5)
    assert huella.nitidez >= 0


@pytest.mark.marca("RF-04 · C1")
def test_yunet_real_no_ve_caras_en_un_recorte_gris(vision_real) -> None:
    assert vision_real.detectar(np.full((150, 120, 3), 128, dtype=np.uint8)) == []


@pytest.mark.marca("RF-04 · C4")
def test_decodificar_no_toca_el_disco_y_rechaza_lo_que_no_es_jpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cv2, "imread", lambda *_: pytest.fail("La imagen se lee del cuerpo, nunca de un archivo."))
    imagen = np.zeros((20, 30, 3), dtype=np.uint8)
    jpeg = cv2.imencode(".jpg", imagen)[1].tobytes()
    png = cv2.imencode(".png", imagen)[1].tobytes()

    assert decodificar_jpeg(jpeg).shape == (20, 30, 3)
    assert decodificar_jpeg(png) is None
    assert decodificar_jpeg(b"") is None


# --- Fórmula del recorte: los mismos casos del firmware y del simulador ---


@pytest.mark.parametrize(
    "caso",
    [pytest.param(caso, marks=pytest.mark.marca(f"contrato recorte · {caso['nombre']}"), id=caso["nombre"]) for caso in CASOS],
)
def test_el_recorte_cumple_la_formula_del_contrato(caso: dict) -> None:
    ancho, alto = caso["cuadro"]["ancho"], caso["cuadro"]["alto"]
    esperado = caso["esperado"]
    caras = [Cara(x=c["x"], y=c["y"], ancho=c["w"], alto=c["h"], puntaje=0.95) for c in caso["caras"]]

    elegida = cara_mas_grande(caras)

    assert elegida is caras[esperado["cara"]]
    assert caja_del_recorte(elegida, ancho, alto) == (esperado["x0"], esperado["y0"], esperado["x1"], esperado["y1"])

    # De punta a punta sobre un cuadro completo, como lo hará el servidor con una cámara que envíe cuadros.
    vision = VisionFalsa()
    vision.preparar([CaraArmada(x=c["x"], y=c["y"], ancho=c["w"], alto=c["h"]) for c in caso["caras"]])
    cuadro = np.arange(alto * ancho, dtype=np.int32).reshape(alto, ancho)  # cada píxel dice dónde está
    recorte = recortar_cara_mas_grande(cuadro, vision)
    assert recorte.shape == (esperado["alto"], esperado["ancho"])
    assert recorte[0, 0] == esperado["y0"] * ancho + esperado["x0"]
    assert recorte[-1, -1] == (esperado["y1"] - 1) * ancho + (esperado["x1"] - 1)


@pytest.mark.marca("contrato recorte · sin cara")
def test_sin_cara_valida_no_hay_recorte() -> None:
    vision = VisionFalsa()
    vision.preparar([CaraArmada(puntaje=0.5)])

    assert recortar_cara_mas_grande(np.zeros((240, 320, 3), dtype=np.uint8), vision) is None


# --- RNF-01 · C1: la imagen no se guarda ni se registra ---


@pytest.mark.marca("RNF-01 · C1")
def test_procesar_recortes_no_escribe_archivos_ni_registra_la_imagen(
    sesion: TestClient,
    camaras,
    conexion: Connection,
    app,
    vision_real,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture,
    tmp_path: Path,
) -> None:
    def prohibido(*_args, **_kwargs):
        raise AssertionError("Se llamó a cv2.imwrite: la imagen nunca se escribe en disco (RNF-01).")

    monkeypatch.setattr(cv2, "imwrite", prohibido)
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="accesia")
    camara = camaras()
    ana = armar.inscrita(conexion, "Ana María Gómez", "1075000001", eje(0))
    ruido = np.random.default_rng(3).integers(0, 256, (150, 120, 3), dtype=np.uint8)
    datos = cv2.imencode(".jpg", ruido, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()

    respuestas = [
        camara.enviar(CaraArmada(huella=eje(0)), datos=datos),  # permitido
        camara.enviar(CaraArmada(huella=eje(3)), datos=datos),  # desconocido
        camara.enviar(datos=datos),  # descartado
    ]
    sesion.post("/api/v1/inscripciones", json={"persona_id": str(ana), "dispositivo": "entrada"})
    respuestas += [camara.enviar(CaraArmada(huella=eje(0)), datos=datos), camara.enviar(datos=datos)]
    app.state.vision = vision_real  # y con YuNet y SFace reales
    respuestas.append(camara.enviar(datos=datos))

    assert [r.status_code for r in respuestas] == [200] * 6
    salida = capfd.readouterr()
    rastros = [
        base64.b64encode(datos).decode("ascii")[:60],
        base64.b64encode(datos[100:400]).decode("ascii")[:60],
        datos[:64].hex(),
        str(datos[:32])[2:-1],
    ]
    for texto in (caplog.text, salida.out, salida.err):
        for rastro in rastros:
            assert rastro not in texto, "La imagen o su base64 apareció en los registros"
    assert list(tmp_path.iterdir()) == [], "Procesar un recorte escribió archivos"


# --- Registro: los avisos INFO del servidor salen (antes uvicorn solo dejaba WARNING y ERROR) ---


@pytest.mark.marca("registro · INFO")
def test_los_avisos_info_salen_en_el_registro_del_proceso() -> None:
    codigo = (
        "import logging\n"
        "from accesia.main import crear_app\n"
        "crear_app()\n"
        "logging.getLogger('accesia.prueba').info('aviso de prueba de nivel INFO')\n"
        "logging.getLogger('accesia.prueba').debug('aviso de nivel DEBUG')\n"
    )
    entorno = {
        **os.environ,
        "SESION_SECRETO": "secreto",
        "DATABASE_URL": "postgresql://nadie@127.0.0.1:9/nada",
        "PYTHONIOENCODING": "utf-8",
    }

    resultado = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, encoding="utf-8", timeout=120, env=entorno
    )

    assert resultado.returncode == 0, resultado.stderr
    [linea] = [linea for linea in resultado.stderr.splitlines() if "aviso de prueba" in linea]
    assert " INFO accesia.prueba: aviso de prueba de nivel INFO" in linea
    assert linea.split(" ", 1)[0].endswith("-05:00"), "La hora del registro va en hora de Colombia (R8)"
    assert "DEBUG" not in resultado.stderr
