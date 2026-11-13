"""
Nombre: configuracion.py
Descripción: Ruta verConfiguracion: los valores de las reglas que usa el servidor, leídos de infra/.env, los modelos de detección y de huella, y la versión (solo lectura, D-14).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from fastapi import APIRouter, Depends

from accesia import __version__, esquemas
from accesia.config import configuracion
from accesia.modelos import SFACE, YUNET
from accesia.sesion import administrador_actual

router = APIRouter(prefix="/api/v1", tags=["Configuración"], dependencies=[Depends(administrador_actual)])


@router.get("/configuracion", response_model=esquemas.Configuracion, operation_id="verConfiguracion")
def ver_configuracion() -> esquemas.Configuracion:
    """D-14: las reglas se cambian en infra/.env y se reinicia el servidor; la web solo las muestra."""
    conf = configuracion()
    return esquemas.Configuracion(
        umbral_similitud=conf.umbral_similitud,
        ventana_repetido_s=conf.ventana_repetido_s,
        alerta_desconocidos=conf.alerta_desconocidos,
        alerta_ventana_s=conf.alerta_ventana_s,
        inscripcion_muestras=conf.inscripcion_muestras,
        inscripcion_vence_s=conf.inscripcion_vence_s,
        cara_min_px=conf.cara_min_px,
        nitidez_min=conf.nitidez_min,
        zona_horaria=conf.zona_horaria,
        modelo_deteccion=YUNET.nombre,
        modelo_huella=SFACE.nombre,
        version=__version__,
    )
