"""
Nombre: test_cuadro_completo.py
Descripción: Pruebas del contrato cámara → servidor 1.3 (api-dispositivo.md): con X-AccesIA-Imagen: cuadro, la cámara envía el cuadro completo y el servidor hace lo que haría la cámara (la cara más grande, con CARA_MIN_PX y la fórmula del recorte) antes del camino de siempre. Sin la cabecera, todo sigue como un recorte.
Fecha de creación: 2026-11-19
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 1.0
"""

import logging

import armar
import cv2
import numpy as np
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from vision_falsa import CaraArmada, eje

from accesia.rostros import LIMITE_BYTES

ANA = "Ana María Gómez"
CUADRO = {"X-AccesIA-Imagen": "cuadro"}

# Un cuadro QVGA (320 × 240) en JPEG de calidad 80, como el de la cámara: la visión armada no mira sus píxeles.
_ok, _jpeg = cv2.imencode(".jpg", np.full((240, 320, 3), 128, dtype=np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 80])
QVGA = _jpeg.tobytes()

# El caso «Dos caras» de la fórmula del recorte (api-dispositivo.md y casos-recorte.json): la segunda tiene mayor área.
PEQUENA_DEL_CASO = CaraArmada(x=40, y=50, ancho=60, alto=70, huella=eje(5))
GRANDE_DEL_CASO = CaraArmada(x=150, y=60, ancho=80, alto=100, huella=eje(0))


def _respuesta(respuesta) -> dict:
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    validar("RespuestaRostro", cuerpo)
    return cuerpo


def _error(respuesta, estado: int, codigo: str) -> None:
    assert respuesta.status_code == estado, respuesta.text
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == codigo


@pytest.mark.marca("contrato cámara · cuadro")
def test_con_un_cuadro_reconoce_por_el_recorte_de_la_cara_mas_grande(camaras, conexion: Connection, vision) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))

    cuerpo = _respuesta(camara.enviar(PEQUENA_DEL_CASO, GRANDE_DEL_CASO, datos=QVGA, cabeceras=CUADRO))

    assert (cuerpo["resultado"], cuerpo["persona"]["id"]) == ("permitido", str(ana))
    # Primero el cuadro completo; después el recorte de la más grande, de (130, 35) a (250, 185): 120 × 150.
    assert vision.formas[:2] == [(240, 320), (150, 120)]


@pytest.mark.marca("contrato cámara · cuadro")
def test_un_cuadro_sin_cara_da_descartado_sin_cara(camaras, conexion: Connection) -> None:
    camara = camaras()

    cuerpo = _respuesta(camara.enviar(datos=QVGA, cabeceras=CUADRO))

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["evento_id"]) == ("descartado", "sin_cara", None)
    assert armar.eventos(conexion) == []


@pytest.mark.marca("contrato cámara · cuadro")
def test_con_un_cuadro_la_cara_debe_medir_cara_min_px_y_no_el_80_por_ciento(camaras, conexion: Connection) -> None:
    # 70 px está entre 0,8 × 80 y 80: como recorte se procesa (las cajas de ESP-DL y de YuNet no miden igual), pero
    # con un cuadro la detecta el mismo YuNet del servidor, así que vale CARA_MIN_PX, como en la cámara.
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    cara = CaraArmada(alto=70, huella=eje(0))

    como_cuadro = _respuesta(camara.enviar(cara, datos=QVGA, cabeceras=CUADRO))
    como_recorte = _respuesta(camara.enviar(cara, datos=QVGA))

    assert (como_cuadro["resultado"], como_cuadro["motivo"]) == ("descartado", "cara_pequena")
    assert como_recorte["resultado"] == "permitido"


@pytest.mark.marca("contrato cámara · cuadro")
def test_sin_la_cabecera_o_con_recorte_el_cuerpo_es_un_recorte(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    cara = CaraArmada(alto=70, huella=eje(0))

    sin_cabecera = _respuesta(camara.enviar(cara))
    con_recorte = _respuesta(camara.enviar(cara, cabeceras={"X-AccesIA-Imagen": "recorte"}))

    assert (sin_cabecera["resultado"], con_recorte["resultado"]) == ("permitido", "permitido")


@pytest.mark.marca("contrato cámara · cuadro")
@pytest.mark.parametrize(
    ("caras", "resultado", "motivo"),
    [
        ([CaraArmada()], "muestra_aceptada", None),
        ([], "muestra_rechazada", "sin_cara"),
        ([CaraArmada(alto=70)], "muestra_rechazada", "cara_pequena"),
    ],
    ids=["aceptada", "sin cara", "cara pequeña"],
)
def test_un_cuadro_tambien_inscribe(
    sesion: TestClient, camaras, conexion: Connection, caras: list, resultado: str, motivo
) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001")
    sesion.post("/api/v1/inscripciones", json={"persona_id": str(ana), "dispositivo": "entrada"})

    cuerpo = _respuesta(camara.enviar(*caras, datos=QVGA, cabeceras=CUADRO))

    assert (cuerpo["modo"], cuerpo["resultado"], cuerpo["motivo"]) == ("inscribir", resultado, motivo)
    assert cuerpo["persona"]["id"] == str(ana)


@pytest.mark.marca("R7 · tolerancia de tamaño con un cuadro")
def test_r7_con_un_cuadro_la_cara_de_70_px_es_pequena(sesion: TestClient, camaras, conexion: Connection) -> None:
    # reglas.md: la misma cara de 70 px que como recorte da muestra_aceptada (70 ≥ 64), en un cuadro es pequeña.
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001")
    sesion.post("/api/v1/inscripciones", json={"persona_id": str(ana), "dispositivo": "entrada"})

    cuerpo = _respuesta(camara.enviar(CaraArmada(alto=70, nitidez=150), datos=QVGA, cabeceras=CUADRO))

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "cara_pequena")


@pytest.mark.marca("contrato cámara · 422")
@pytest.mark.parametrize("valor", ["foto", "CUADRO", ""])
def test_una_cabecera_de_imagen_que_no_es_recorte_ni_cuadro_da_422(camaras, valor: str) -> None:
    camara = camaras()

    _error(camara.enviar(CaraArmada(), datos=QVGA, cabeceras={"X-AccesIA-Imagen": valor}), 422, "validacion")


@pytest.mark.marca("contrato cámara · 413")
def test_un_cuadro_tambien_tiene_el_tope_de_100_kb(camaras) -> None:
    camara = camaras()
    grande = QVGA + b"\x00" * (LIMITE_BYTES + 1 - len(QVGA))

    _error(camara.enviar(datos=grande, cabeceras=CUADRO), 413, "imagen_grande")


@pytest.mark.marca("contrato cámara · orden")
def test_la_cabecera_de_imagen_va_despues_del_tipo_y_antes_del_tamano(camaras) -> None:
    activa = camaras("entrada")
    inactiva = camaras("salida", activo=False)
    mala = {"X-AccesIA-Imagen": "foto"}
    grande = QVGA + b"\x00" * (LIMITE_BYTES + 1 - len(QVGA))

    assert inactiva.enviar(datos=grande, cabeceras=mala).status_code == 403
    assert activa.enviar(datos=grande, tipo="image/png", cabeceras=mala).status_code == 415
    _error(activa.enviar(datos=grande, cabeceras=mala), 422, "validacion")


@pytest.mark.marca("contrato cámara · cuadro")
def test_el_registro_dice_que_llego_un_cuadro(camaras, conexion: Connection, caplog) -> None:
    caplog.set_level(logging.INFO, logger="accesia")
    camara = camaras()

    camara.enviar(datos=QVGA, cabeceras=CUADRO)
    camara.enviar(CaraArmada(), datos=QVGA)

    lineas = [r.getMessage() for r in caplog.records if r.getMessage().startswith("Cámara entrada ·")]
    assert len(lineas) == 2
    assert "cuadro" in lineas[0] and "cuadro" not in lineas[1]
