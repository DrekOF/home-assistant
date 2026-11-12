"""
Nombre: webcam.py
Descripción: Modo webcam: una ventana con la imagen, la caja de la cara elegida y el último mensaje del servidor; se cierra con q o Esc y no guarda cuadros ni recortes.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import threading
import time
from collections.abc import Callable
from typing import Protocol

import cv2
import numpy as np

from simulador.consola import linea_respuesta, mensaje_corto, sin_tildes
from simulador.envio import ClienteCamara, Respuesta
from simulador.imagen import preparar
from simulador.recortador import Envio, Recortador, SinEnvio
from simulador.ritmo import Ritmo

# En ASCII: la ventana de OpenCV en Windows no muestra bien otros caracteres en el título.
TITULO = "AccesIA - simulador (q o Esc para salir)"
TECLAS_SALIR = (ord("q"), ord("Q"), 27)
VERDE = (60, 200, 60)
NARANJA = (0, 165, 255)


class Captura(Protocol):
    def isOpened(self) -> bool: ...  # noqa: N802 (nombre de OpenCV)
    def read(self) -> tuple[bool, np.ndarray | None]: ...
    def release(self) -> None: ...


class Ventana(Protocol):
    def mostrar(self, imagen: np.ndarray) -> bool:
        """Muestra la imagen; False si la persona pidió cerrar."""
        ...

    def cerrar(self) -> None: ...


class VentanaOpenCV:
    def __init__(self, titulo: str = TITULO) -> None:
        self.titulo = titulo
        cv2.namedWindow(titulo, cv2.WINDOW_AUTOSIZE)

    def mostrar(self, imagen: np.ndarray) -> bool:
        cv2.imshow(self.titulo, imagen)
        if (cv2.waitKey(1) & 0xFF) in TECLAS_SALIR:
            return False
        try:  # cerrada con la X
            return cv2.getWindowProperty(self.titulo, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:
            return False

    def cerrar(self) -> None:
        cv2.destroyAllWindows()


def abrir_webcam(indice: int) -> Captura:
    return cv2.VideoCapture(indice)


class EnvioEnSegundoPlano:
    """Envía un recorte a la vez en otro hilo, para que la ventana no se congele mientras responde el servidor."""

    def __init__(self, cliente: ClienteCamara, ritmo: Ritmo, salida: Callable[[str], None]) -> None:
        self._cliente = cliente
        self._ritmo = ritmo
        self._salida = salida
        self._hilo: threading.Thread | None = None
        self._candado = threading.Lock()
        self._ultimo = "Esperando una cara"

    @property
    def ultimo(self) -> str:
        with self._candado:
            return self._ultimo

    def ocupado(self) -> bool:
        return self._hilo is not None and self._hilo.is_alive()

    def enviar(self, envio: Envio) -> None:
        self._hilo = threading.Thread(target=self._enviar, args=(envio,), daemon=True)
        self._hilo.start()

    def _enviar(self, envio: Envio) -> None:
        try:
            respuesta = self._cliente.enviar(envio.jpeg, envio.puntaje)
        except Exception as error:  # noqa: BLE001 — un error raro cuenta como falla y espera, no reintenta en cada cuadro
            respuesta = Respuesta(None, falla=f"error al enviar ({type(error).__name__})")
        espera = self._ritmo.registrar(respuesta)
        self._salida(f"{time.strftime('%H:%M:%S')} {linea_respuesta(respuesta, espera)}")
        with self._candado:
            self._ultimo = mensaje_corto(respuesta)

    def terminar(self, segundos: float = 6.0) -> None:
        if self._hilo is not None:
            self._hilo.join(segundos)


def dibujar(imagen: np.ndarray, resultado: Envio | SinEnvio, mensaje: str) -> np.ndarray:
    """Una copia para la ventana, con la caja de la cara elegida y dos líneas de texto.

    Si la imagen es de 320 × 240 (modo «como la cámara»), se muestra al doble.
    """
    escala = 2 if imagen.shape[1] < 640 else 1
    vista = cv2.resize(imagen, None, fx=escala, fy=escala, interpolation=cv2.INTER_NEAREST)

    caja = resultado.caja
    if caja is not None:
        color = VERDE if isinstance(resultado, Envio) else NARANJA
        esquina1 = (round(caja.x * escala), round(caja.y * escala))
        esquina2 = (round((caja.x + caja.w) * escala), round((caja.y + caja.h) * escala))
        cv2.rectangle(vista, esquina1, esquina2, color, 2)

    estado = "Cara lista para enviar" if isinstance(resultado, Envio) else resultado.detalle
    alto, ancho = vista.shape[:2]
    cv2.rectangle(vista, (0, alto - 52), (ancho, alto), (0, 0, 0), -1)
    for fila, texto in enumerate((mensaje, estado)):
        cv2.putText(vista, sin_tildes(texto), (8, alto - 32 + fila * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1, cv2.LINE_AA)
    return vista


def correr_webcam(
    recortador: Recortador,
    cliente: ClienteCamara,
    ritmo: Ritmo,
    *,
    modo_camara: bool,
    indice: int = 0,
    abrir: Callable[[int], Captura] = abrir_webcam,
    crear_ventana: Callable[[], Ventana] = VentanaOpenCV,
    salida: Callable[[str], None] = print,
) -> int:
    captura = abrir(indice)
    if not captura.isOpened():
        salida(f"No se pudo abrir la webcam {indice}. Prueba con otra: --camara 1")
        return 2

    ventana = crear_ventana()
    envios = EnvioEnSegundoPlano(cliente, ritmo, salida)
    ultimo_aviso = -float("inf")
    try:
        while True:
            ok, cuadro = captura.read()
            if not ok or cuadro is None:
                salida("La webcam dejó de entregar imágenes.")
                return 1

            imagen = preparar(cuadro, modo_camara)
            resultado = recortador.procesar(imagen)
            if isinstance(resultado, Envio):
                if not envios.ocupado() and ritmo.puede_enviar():
                    envios.enviar(resultado)
            elif resultado.motivo == "recorte_grande" and time.monotonic() - ultimo_aviso >= 2:
                salida(resultado.detalle)
                ultimo_aviso = time.monotonic()

            if not ventana.mostrar(dibujar(imagen, resultado, envios.ultimo)):
                return 0
    except KeyboardInterrupt:
        return 0
    finally:
        captura.release()
        ventana.cerrar()
        envios.terminar()
