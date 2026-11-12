"""
Nombre: dobles.py
Descripción: Dobles de prueba del simulador: detector, reloj, servidor (httpx.MockTransport), webcam y ventana falsos, y fotos sintéticas sin caras.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np

from simulador.envio import ClienteCamara
from simulador.recorte import Cara

# Si este texto aparece en la salida, el simulador mostró el token.
TOKEN = "token-de-prueba-que-nunca-se-muestra"
SERVIDOR = "http://servidor.prueba"


class DetectorFalso:
    """Devuelve las caras que se le dan. Con `por_llamada`, una lista por llamada (una por foto o por cuadro)."""

    def __init__(self, caras: Sequence[Cara] = (), *, por_llamada: Sequence[Sequence[Cara]] | None = None) -> None:
        self._caras = list(caras)
        self._por_llamada = [list(lista) for lista in por_llamada] if por_llamada is not None else None
        self.formas: list[tuple[int, ...]] = []

    def detectar(self, imagen: np.ndarray) -> list[Cara]:
        self.formas.append(imagen.shape)
        if self._por_llamada is None:
            return list(self._caras)
        indice = len(self.formas) - 1
        return list(self._por_llamada[indice]) if indice < len(self._por_llamada) else []


class RelojFalso:
    """Reloj que solo avanza cuando se le pide: sirve de reloj del Ritmo y de `dormir`."""

    def __init__(self, inicio: float = 1000.0) -> None:
        self.ahora = inicio
        self.dormidas: list[float] = []

    def __call__(self) -> float:
        return self.ahora

    def dormir(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.ahora += segundos


def cuerpo_200(
    resultado: str,
    *,
    modo: str = "reconocer",
    motivo: str | None = None,
    persona: str | None = None,
    similitud: float | None = None,
    repetido: bool = False,
    inscripcion: dict[str, Any] | None = None,
    mensaje: str = "",
) -> dict[str, Any]:
    """Una respuesta 200 con todos los campos del contrato (api-dispositivo.md · Respuesta 200)."""
    return {
        "modo": modo,
        "resultado": resultado,
        "motivo": motivo,
        "persona": None if persona is None else {"id": "01a1e5c2-7f3a-7b2c-9d4e-5f6a7b8c9d0e", "nombre": persona},
        "similitud": similitud,
        "repetido": repetido,
        "evento_id": None,
        "inscripcion": inscripcion,
        "mensaje": mensaje,
        "hora": "2026-11-20T07:58:12-05:00",
    }


def respuesta_200(resultado: str, **campos: Any) -> httpx.Response:
    return httpx.Response(200, json=cuerpo_200(resultado, **campos))


def respuesta_error(estado: int, codigo: str, cabeceras: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(estado, json={"detalle": f"error {codigo}", "codigo": codigo}, headers=cabeceras)


Siguiente = httpx.Response | Exception | Callable[[httpx.Request], httpx.Response]


class ServidorFalso:
    """Servidor con httpx.MockTransport: guarda cada petición y responde, en orden, lo que se le dio.

    Cuando se acaban las respuestas, contesta `descartado`. `al_recibir` corre con cada petición (por ejemplo,
    para que el reloj falso avance lo que tarda el servidor).
    """

    def __init__(self, *respuestas: Siguiente, al_recibir: Callable[[httpx.Request], None] | None = None) -> None:
        self.respuestas: list[Siguiente] = list(respuestas)
        self.peticiones: list[httpx.Request] = []
        self.al_recibir = al_recibir

    def _manejar(self, peticion: httpx.Request) -> httpx.Response:
        peticion.read()
        self.peticiones.append(peticion)
        if self.al_recibir is not None:
            self.al_recibir(peticion)
        siguiente = self.respuestas.pop(0) if self.respuestas else respuesta_200("descartado", motivo="sin_cara")
        if isinstance(siguiente, Exception):
            raise siguiente
        if callable(siguiente):
            return siguiente(peticion)
        return siguiente

    def cliente(self, codigo: str = "entrada") -> ClienteCamara:
        return ClienteCamara(SERVIDOR, codigo, TOKEN, transporte=httpx.MockTransport(self._manejar))


class CapturaFalsa:
    """Webcam falsa: entrega los cuadros que se le dan y después falla, como una cámara desconectada."""

    def __init__(self, cuadros: Sequence[np.ndarray], abierta: bool = True) -> None:
        self._cuadros = list(cuadros)
        self._abierta = abierta
        self.liberada = False

    def isOpened(self) -> bool:  # noqa: N802 (nombre de OpenCV)
        return self._abierta

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._cuadros:
            return False, None
        return True, self._cuadros.pop(0)

    def release(self) -> None:
        self.liberada = True


class VentanaFalsa:
    """Ventana falsa: muestra `cuadros` imágenes y después responde como si la persona pulsara q."""

    def __init__(self, cuadros: int) -> None:
        self._faltan = cuadros
        self.formas: list[tuple[int, ...]] = []
        self.cerrada = False

    def mostrar(self, imagen: np.ndarray) -> bool:
        self.formas.append(imagen.shape)
        self._faltan -= 1
        return self._faltan > 0

    def cerrar(self) -> None:
        self.cerrada = True


def imagen_sintetica(ancho: int, alto: int, semilla: int = 0) -> np.ndarray:
    """Degradado con unas figuras: no es una cara, pero tampoco es plana (el JPEG tiene algo que comprimir)."""
    generador = np.random.default_rng(semilla)
    columnas = np.linspace(0, 255, ancho, dtype=np.float32)
    filas = np.linspace(0, 255, alto, dtype=np.float32)[:, None]
    imagen = np.stack([columnas + 0 * filas, filas + 0 * columnas, (columnas + filas) / 2], axis=2).astype(np.uint8)
    for _ in range(6):
        centro = (int(generador.integers(0, ancho)), int(generador.integers(0, alto)))
        color = tuple(int(c) for c in generador.integers(0, 256, 3))
        cv2.circle(imagen, centro, int(generador.integers(5, max(6, min(ancho, alto) // 6))), color, -1)
    return imagen


def ruido(ancho: int, alto: int, semilla: int = 0) -> np.ndarray:
    """Ruido puro: su JPEG pesa mucho, sirve para pasar de 100 000 bytes."""
    return np.random.default_rng(semilla).integers(0, 256, (alto, ancho, 3), dtype=np.uint8)


def escribir_foto(ruta: Path, imagen: np.ndarray) -> Path:
    """Escribe una foto sintética de entrada para el modo carpeta (la prueba la crea; el simulador solo la lee)."""
    ok, datos = cv2.imencode(ruta.suffix, imagen)
    assert ok
    ruta.write_bytes(datos.tobytes())
    return ruta
