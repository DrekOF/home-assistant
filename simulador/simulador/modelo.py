"""
Nombre: modelo.py
Descripción: Modelo YuNet del simulador: se descarga la primera vez a datos/modelos/ desde un commit fijo de opencv_zoo y se comprueba con su SHA-256.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import hashlib
from collections.abc import Callable
from pathlib import Path

import httpx

from simulador.rutas import MODELOS

# El mismo archivo, URL y hash que el servidor (specs/arquitectura.md, Piezas).
OPENCV_ZOO_COMMIT = "48b10fa505aeb51fbd127fc60a5c660040e823b7"
YUNET_ARCHIVO = "face_detection_yunet_2023mar.onnx"
# opencv_zoo guarda los modelos con Git LFS: raw.githubusercontent.com devuelve el puntero de LFS;
# github.com/…/raw/… redirige al modelo.
YUNET_URL = (
    f"https://github.com/opencv/opencv_zoo/raw/{OPENCV_ZOO_COMMIT}"
    f"/models/face_detection_yunet/{YUNET_ARCHIVO}"
)
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
YUNET_BYTES = 232_589


class ErrorModelo(Exception):
    """El modelo no se pudo descargar o no coincide con su SHA-256."""


def sha256_de(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 16), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def descargar_url(url: str, destino: Path) -> None:
    with httpx.stream("GET", url, follow_redirects=True, timeout=30.0) as respuesta:
        respuesta.raise_for_status()
        with destino.open("wb") as archivo:
            for bloque in respuesta.iter_bytes():
                archivo.write(bloque)


def asegurar_modelo(
    carpeta: Path = MODELOS,
    *,
    url: str = YUNET_URL,
    sha256: str = YUNET_SHA256,
    archivo: str = YUNET_ARCHIVO,
    descargar: Callable[[str, Path], None] = descargar_url,
    avisar: Callable[[str], None] = print,
) -> Path:
    """Devuelve la ruta del modelo. Si falta o no coincide con su SHA-256, lo descarga y lo comprueba.

    Con el modelo ya descargado no usa la red: en clase no hay internet (RNF-04 · C3).
    """
    destino = carpeta / archivo
    if destino.exists():
        if sha256_de(destino) == sha256:
            return destino
        avisar(f"{destino} no coincide con su SHA-256: se descarga otra vez.")

    carpeta.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".parcial")
    avisar(f"Descargando {archivo} de opencv_zoo (commit {OPENCV_ZOO_COMMIT[:7]}).")
    try:
        descargar(url, parcial)
    except (httpx.HTTPError, OSError) as error:
        parcial.unlink(missing_ok=True)
        raise ErrorModelo(
            f"No se pudo descargar {archivo}: {error}. Sin internet, cópialo a {carpeta} desde el kit."
        ) from error

    obtenido = sha256_de(parcial)
    if obtenido != sha256:
        parcial.unlink(missing_ok=True)
        raise ErrorModelo(f"{archivo} no coincide con su SHA-256: se esperaba {sha256} y llegó {obtenido}.")
    parcial.replace(destino)
    return destino
