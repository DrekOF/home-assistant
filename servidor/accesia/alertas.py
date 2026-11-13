"""
Nombre: alertas.py
Descripción: Alerta de desconocidos (R6): cuenta los desconocidos de una cámara en la ventana y después de su última alerta, cuya hora vive en memoria, y arma el mensaje Alerta de mqtt.md.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import logging
import threading
from datetime import datetime, timedelta

from sqlalchemy import Connection, text

from accesia.config import configuracion
from accesia.tiempo import a_colombia

registro = logging.getLogger(__name__)

# R6: guardados hace menos de ALERTA_VENTANA_S (uno de hace exactamente la ventana ya no cuenta), él incluido. Que
# sean posteriores a la última alerta lo asegura revisar(): solo cuenta si ya pasó una ventana desde ella.
CONTAR = """
SELECT count(*) FROM evento_acceso
WHERE dispositivo_codigo = :codigo AND resultado = 'desconocido'
  AND fecha_hora > :desde AND fecha_hora <= :momento
"""


class ControlDeAlertas:
    """La hora de la última alerta de cada cámara. Vive en memoria, como permite R6: el servidor corre con un solo
    proceso y, si se reinicia, empieza de cero."""

    def __init__(self) -> None:
        self._ultima: dict[str, datetime] = {}
        self._candado = threading.Lock()

    def revisar(self, conexion: Connection, codigo: str, momento: datetime) -> dict | None:
        """Se llama al guardar un desconocido, en su misma transacción. Devuelve la Alerta si corresponde."""
        conf = configuracion()
        ventana = timedelta(seconds=conf.alerta_ventana_s)
        with self._candado:
            ultima = self._ultima.get(codigo)
            if ultima is not None and momento - ultima < ventana:
                return None  # una sola alerta por ventana
            # Si se llega aquí, la última alerta tiene una ventana o más: todo lo que cae en la ventana ya es posterior
            # a ella. Por eso basta con contar la ventana.
            cuantos = conexion.execute(
                text(CONTAR), {"codigo": codigo, "desde": momento - ventana, "momento": momento}
            ).scalar_one()
            if cuantos < conf.alerta_desconocidos:
                return None
            self._ultima[codigo] = momento
        registro.info("Alerta R6 en la cámara %s: %d desconocidos en %d s.", codigo, cuantos, conf.alerta_ventana_s)
        return {
            "dispositivo": codigo,
            "desconocidos": cuantos,
            "ventana_s": conf.alerta_ventana_s,
            "hora": a_colombia(momento).isoformat(),
        }
