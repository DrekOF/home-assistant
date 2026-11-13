"""
Nombre: test_privacidad.py
Descripción: Prueba de RNF-01 · C1 en el simulador: ningún modo escribe imágenes, tampoco con --puerta; falla si se llama a cv2.imwrite, si se abre un archivo para escribir o si aparece un archivo de imagen.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
"""

import builtins
import io
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import cv2
import pytest
from dobles import (
    CLAVE_MQTT,
    CapturaFalsa,
    DetectorFalso,
    FabricaMqtt,
    RelojFalso,
    ServidorFalso,
    VentanaFalsa,
    escribir_foto,
    imagen_sintetica,
    preparar_principal,
)

from simulador.carpeta import correr_carpeta
from simulador.comandos import principal
from simulador.mqtt import Broker, PuertaMqtt
from simulador.recortador import RecortadorYuNet
from simulador.recorte import Cara
from simulador.ritmo import Ritmo
from simulador.rutas import RAIZ
from simulador.webcam import correr_webcam

pytestmark = pytest.mark.marca("RNF-01 · C1")

EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".gif", ".ppm", ".pgm"}
NO_REVISAR = {".venv", ".git", "node_modules", "__pycache__", ".pytest_cache"}


def _imagenes_en(*carpetas: Path) -> set[Path]:
    encontradas = set()
    for carpeta in carpetas:
        for raiz, subcarpetas, archivos in os.walk(carpeta):
            subcarpetas[:] = [nombre for nombre in subcarpetas if nombre not in NO_REVISAR]
            encontradas.update(Path(raiz, nombre) for nombre in archivos
                               if Path(nombre).suffix.lower() in EXTENSIONES_IMAGEN)
    return encontradas


@contextmanager
def sin_escribir(monkeypatch: pytest.MonkeyPatch, *carpetas: Path) -> Iterator[None]:
    """Mientras dura, escribir una imagen o cualquier archivo hace fallar la prueba.

    Al final no puede haber imágenes nuevas en las carpetas dadas.
    """

    def prohibido(*_args, **_kwargs):
        raise AssertionError("el simulador intentó guardar una imagen o un video")

    for nombre in ("imwrite", "imwritemulti", "imwriteanimation", "VideoWriter"):
        if hasattr(cv2, nombre):
            monkeypatch.setattr(cv2, nombre, prohibido)

    abrir = io.open

    def abrir_solo_para_leer(archivo, modo="r", *args, **kwargs):
        if any(letra in modo for letra in "wax+"):
            raise AssertionError(f"el simulador intentó escribir {archivo}")
        return abrir(archivo, modo, *args, **kwargs)

    antes = _imagenes_en(*carpetas)
    monkeypatch.setattr(builtins, "open", abrir_solo_para_leer)
    monkeypatch.setattr(io, "open", abrir_solo_para_leer)
    try:
        yield
    finally:
        monkeypatch.setattr(builtins, "open", abrir)
        monkeypatch.setattr(io, "open", abrir)
    assert _imagenes_en(*carpetas) == antes, "apareció un archivo de imagen"


@pytest.mark.parametrize("modo_camara", [False, True], ids=["normal", "como la cámara"])
def test_modo_carpeta_no_escribe_imagenes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, modo_camara: bool
) -> None:
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for numero in range(3):
        escribir_foto(fotos / f"foto-{numero}.jpg", imagen_sintetica(1280, 720, numero))
    trabajo = tmp_path / "trabajo"
    trabajo.mkdir()
    monkeypatch.chdir(trabajo)

    with sin_escribir(monkeypatch, tmp_path, RAIZ / "simulador", RAIZ / "datos"):
        codigo = correr_carpeta(
            fotos, RecortadorYuNet(DetectorFalso([Cara(100, 60, 90, 110)])), servidor.cliente(), Ritmo(),
            modo_camara=modo_camara, dormir=lambda _: None, salida=lambda _: None,
        )

    assert codigo == 0
    assert len(servidor.peticiones) == 3  # sí detectó, recortó y envió: no pasó por alto el trabajo


@pytest.mark.parametrize("modo_camara", [False, True], ids=["normal", "como la cámara"])
def test_modo_webcam_no_escribe_imagenes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, modo_camara: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    captura = CapturaFalsa([imagen_sintetica(1280, 720, numero) for numero in range(5)])

    with sin_escribir(monkeypatch, tmp_path, RAIZ / "simulador", RAIZ / "datos"):
        codigo = correr_webcam(
            RecortadorYuNet(DetectorFalso([Cara(100, 60, 90, 110)])), servidor.cliente(), Ritmo(),
            modo_camara=modo_camara, abrir=lambda _: captura, crear_ventana=lambda: VentanaFalsa(5),
            salida=lambda _: None,
        )

    assert codigo == 0
    assert captura.liberada
    assert len(servidor.peticiones) == 1


@pytest.mark.parametrize("modo_camara", [False, True], ids=["normal", "como la cámara"])
def test_modo_carpeta_con_puerta_no_escribe_imagenes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, modo_camara: bool
) -> None:
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for numero in range(3):
        escribir_foto(fotos / f"foto-{numero}.jpg", imagen_sintetica(1280, 720, numero))
    trabajo = tmp_path / "trabajo"
    trabajo.mkdir()
    monkeypatch.chdir(trabajo)
    creados = preparar_principal(monkeypatch, servidor, [Cara(100, 60, 90, 110)])
    opciones = ["--como-camara"] if modo_camara else []

    with sin_escribir(monkeypatch, tmp_path, RAIZ / "simulador", RAIZ / "datos"):
        codigo = principal(["carpeta", str(fotos), "--codigo", "entrada", "--puerta", *opciones])

    assert codigo == 0
    assert len(creados) == 1 and creados[0].publicados  # la puerta sí se conectó y publicó
    assert len(servidor.peticiones) == 3


def test_modo_webcam_con_la_puerta_abierta_no_escribe_imagenes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso
) -> None:
    monkeypatch.chdir(tmp_path)
    captura = CapturaFalsa([imagen_sintetica(1280, 720, numero) for numero in range(5)])
    fabrica = FabricaMqtt()
    puerta = PuertaMqtt(Broker("localhost"), "entrada", CLAVE_MQTT, reloj=RelojFalso(), salida=lambda _: None,
                        crear_cliente=fabrica)
    [cliente] = fabrica.clientes
    cliente.conectar()
    cliente.recibir("accesia/entrada/puerta/set", b"ABRIR")
    ventana = VentanaFalsa(5)

    with sin_escribir(monkeypatch, tmp_path, RAIZ / "simulador", RAIZ / "datos"):
        codigo = correr_webcam(
            RecortadorYuNet(DetectorFalso([Cara(100, 60, 90, 110)])), servidor.cliente(), Ritmo(),
            modo_camara=False, abrir=lambda _: captura, crear_ventana=lambda: ventana, salida=lambda _: None,
            puerta=puerta,
        )

    assert codigo == 0
    assert puerta.aviso() is not None  # la franja «PUERTA ABIERTA» se dibujó en cada cuadro
    assert len(servidor.peticiones) == 1
