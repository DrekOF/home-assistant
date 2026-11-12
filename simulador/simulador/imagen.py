"""
Nombre: imagen.py
Descripción: Imágenes del simulador en memoria: JPEG de calidad 80, lectura de fotos y el modo «como la cámara» (4:3 al centro, 320 × 240 y JPEG 80).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path

import cv2
import numpy as np

# Cuadro de la cámara (QVGA) y calidad del JPEG (specs/arquitectura.md, Firmware · Comportamiento).
ANCHO_CAMARA = 320
ALTO_CAMARA = 240
CALIDAD_JPEG = 80


def codificar_jpeg(imagen: np.ndarray, calidad: int = CALIDAD_JPEG) -> bytes:
    """Comprime en memoria; nunca escribe un archivo (RNF-01 · C1)."""
    ok, datos = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, calidad])
    if not ok:
        raise ValueError("OpenCV no pudo comprimir la imagen en JPEG")
    return datos.tobytes()


def decodificar_jpeg(datos: bytes) -> np.ndarray:
    imagen = cv2.imdecode(np.frombuffer(datos, np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        raise ValueError("OpenCV no pudo leer el JPEG")
    return imagen


def leer_foto(ruta: Path) -> np.ndarray | None:
    """Lee una foto en color, girada según su EXIF; None si no se puede leer.

    Usa np.fromfile y cv2.imdecode porque cv2.imread no abre rutas con tildes en Windows.
    """
    try:
        datos = np.fromfile(ruta, dtype=np.uint8)
    except OSError:
        return None
    if datos.size == 0:
        return None
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def recortar_a_4_3(imagen: np.ndarray) -> np.ndarray:
    """El rectángulo 4:3 más grande, al centro. Una imagen 16:9 pierde los lados; una vertical, arriba y abajo."""
    alto, ancho = imagen.shape[:2]
    if ancho * 3 > alto * 4:
        nuevo_ancho = alto * 4 // 3
        x = (ancho - nuevo_ancho) // 2
        return imagen[:, x : x + nuevo_ancho]
    if ancho * 3 < alto * 4:
        nuevo_alto = ancho * 3 // 4
        y = (alto - nuevo_alto) // 2
        return imagen[y : y + nuevo_alto, :]
    return imagen


def como_camara(imagen: np.ndarray) -> np.ndarray:
    """Deja la imagen como la vería el ESP32-S3: 4:3 al centro, 320 × 240 sin deformar y JPEG 80 de ida y vuelta."""
    reducida = cv2.resize(recortar_a_4_3(imagen), (ANCHO_CAMARA, ALTO_CAMARA), interpolation=cv2.INTER_AREA)
    return decodificar_jpeg(codificar_jpeg(reducida, CALIDAD_JPEG))


def preparar(imagen: np.ndarray, modo_camara: bool) -> np.ndarray:
    """El paso antes de detectar: con `--como-camara` la imagen pasa por como_camara; si no, queda igual."""
    return como_camara(imagen) if modo_camara else imagen
