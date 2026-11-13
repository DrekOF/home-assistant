"""
Nombre: puerta.py
Descripción: La puerta del simulador, igual que PuertaLogica de la placa (PR #11): ABRIR la abre los segundos configurados, CERRAR la cierra antes y cualquier otro mensaje se ignora.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Lógica pura, sin MQTT ni hilos: cada llamada recibe la hora (time.monotonic, en segundos), como la placa recibe
sus milisegundos. Contrato: specs/contratos/mqtt.md, Temas.
"""

from enum import Enum

# «La cámara mantiene la puerta abierta los segundos configurados (3 por defecto)» (mqtt.md, Temas).
SEGUNDOS_POR_DEFECTO = 3
# El mismo rango que acepta el comando «puerta» de la consola de la placa.
SEGUNDOS_MIN = 1
SEGUNDOS_MAX = 60

ABIERTA = "abierta"
CERRADA = "cerrada"


class Orden(Enum):
    ABRIR = "ABRIR"
    CERRAR = "CERRAR"


def leer_orden(carga: bytes) -> Orden | None:
    """«ABRIR» o «CERRAR» exactos, como la placa: «abrir», «ABRIR » o cualquier otra cosa no es una orden."""
    for orden in Orden:
        if carga == orden.value.encode("ascii"):
            return orden
    return None


class Puerta:
    """Abierta o cerrada, y cuándo se cierra sola.

    `orden` y `actualizar` devuelven True si la puerta cambió, es decir, si hay que publicar su estado.
    """

    def __init__(self, segundos: float = SEGUNDOS_POR_DEFECTO) -> None:
        self.segundos = segundos
        self._abierta = False
        self._cierra_en = 0.0

    @property
    def abierta(self) -> bool:
        return self._abierta

    @property
    def estado(self) -> str:
        """El mensaje de accesia/{codigo}/puerta/estado: «abierta» o «cerrada»."""
        return ABIERTA if self._abierta else CERRADA

    def orden(self, orden: Orden, ahora: float) -> bool:
        """ABRIR la abre y cuenta los segundos desde ahora; si ya estaba abierta, vuelve a contarlos y no cambia.

        CERRAR la cierra; si ya estaba cerrada, no cambia.
        """
        if orden is Orden.ABRIR:
            cambia = not self._abierta
            self._abierta = True
            self._cierra_en = ahora + self.segundos
            return cambia
        cambia = self._abierta
        self._abierta = False
        return cambia

    def actualizar(self, ahora: float) -> bool:
        """Cierra la puerta si ya se cumplió su tiempo; True si se cerró en esta llamada."""
        if self._abierta and ahora >= self._cierra_en:
            self._abierta = False
            return True
        return False

    def faltan(self, ahora: float) -> float:
        """Segundos que faltan para que se cierre sola (0 si está cerrada)."""
        return max(0.0, self._cierra_en - ahora) if self._abierta else 0.0
