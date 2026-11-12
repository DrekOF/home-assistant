"""
Nombre: modelos.py
Descripción: Modelos de cara del servidor (YuNet y SFace de opencv/opencv_zoo, en un commit fijo): dónde viven, su SHA-256 y su descarga comprobada.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Solo usa la biblioteca estándar: el Dockerfile lo corre solo, sin instalar el servidor, para descargar los modelos
al construir la imagen (python modelos.py --carpeta /app/datos/modelos).
"""

import argparse
import hashlib
import os
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# opencv_zoo guarda los modelos con Git LFS: raw.githubusercontent.com devuelve el puntero y no el modelo.
# github.com/<repo>/raw/<commit>/… sí redirige al archivo. El simulador usa el mismo commit (specs/arquitectura.md).
COMMIT = "48b10fa505aeb51fbd127fc60a5c660040e823b7"
_BASE = f"https://github.com/opencv/opencv_zoo/raw/{COMMIT}/models"


@dataclass(frozen=True)
class Modelo:
    archivo: str
    url: str
    sha256: str
    bytes: int


YUNET = Modelo(
    archivo="face_detection_yunet_2023mar.onnx",
    url=f"{_BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    bytes=232_589,
)
SFACE = Modelo(
    archivo="face_recognition_sface_2021dec.onnx",
    url=f"{_BASE}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    bytes=38_696_353,
)
MODELOS = (YUNET, SFACE)


def carpeta_modelos() -> Path:
    """datos/modelos/ desde la raíz del repositorio. En el PC y en la CI es <repositorio>/datos/modelos; en la imagen,
    donde el servidor vive en /app/servidor, es /app/datos/modelos. Git y Docker ignoran datos/."""
    return Path(__file__).resolve().parents[2] / "datos" / "modelos"


def sha256_de(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def problema_de(ruta: Path, modelo: Modelo) -> str | None:
    """Qué tiene de malo el archivo del modelo, o None si está completo y su SHA-256 coincide."""
    if not ruta.is_file():
        return f"falta {ruta}"
    if ruta.stat().st_size != modelo.bytes:
        return f"{ruta.name} pesa {ruta.stat().st_size} bytes y debería pesar {modelo.bytes}"
    if sha256_de(ruta) != modelo.sha256:
        return f"el SHA-256 de {ruta.name} no coincide con el fijado"
    return None


def descargar(carpeta: Path | None = None, avisar: Callable[[str], None] = print) -> list[Path]:
    """Descarga a la carpeta los modelos que falten o no coincidan, y comprueba su tamaño y su SHA-256.

    Lo que ya está y coincide no se vuelve a descargar. Si un archivo no coincide después de bajarlo, no lo deja y
    lanza RuntimeError.
    """
    carpeta = carpeta or carpeta_modelos()
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    for modelo in MODELOS:
        ruta = carpeta / modelo.archivo
        rutas.append(ruta)
        if problema_de(ruta, modelo) is None:
            avisar(f"{modelo.archivo}: ya está y su SHA-256 coincide.")
            continue
        avisar(f"{modelo.archivo}: descargando de opencv_zoo ({modelo.bytes:,} bytes)…".replace(",", " "))
        parcial = ruta.with_name(ruta.name + ".parcial")
        pedido = urllib.request.Request(modelo.url, headers={"User-Agent": "accesia-descargar-modelos"})
        with urllib.request.urlopen(pedido, timeout=60) as respuesta, parcial.open("wb") as destino:
            for bloque in iter(lambda: respuesta.read(1 << 20), b""):
                destino.write(bloque)
        problema = problema_de(parcial, modelo)
        if problema is not None:
            parcial.unlink(missing_ok=True)
            raise RuntimeError(f"La descarga de {modelo.archivo} no sirve: {problema}.")
        os.replace(parcial, ruta)
        avisar(f"{modelo.archivo}: listo, SHA-256 comprobado.")
    return rutas


def principal(argumentos: list[str] | None = None) -> int:
    lector = argparse.ArgumentParser(description="Descarga los modelos de cara del servidor y comprueba su SHA-256.")
    lector.add_argument("--carpeta", type=Path, default=None, help="por defecto, datos/modelos/ del repositorio")
    leidos = lector.parse_args(argumentos)
    try:
        descargar(leidos.carpeta)
    except (OSError, RuntimeError) as error:
        print(f"No se pudieron descargar los modelos: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(principal())
