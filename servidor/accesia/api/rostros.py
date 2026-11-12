"""
Nombre: rostros.py
Descripción: Ruta enviarRostro: la cámara (o el simulador) envía el recorte de una cara con su token (specs/contratos/api-dispositivo.md). No usa la sesión de la web.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from accesia import rostros, tiempo
from accesia.db import Conexion
from accesia.esquemas import RespuestaRostro
from accesia.vision import Vision

router = APIRouter(prefix="/api/v1", tags=["Cámaras"])


def _vision(request: Request) -> Vision:
    vision = getattr(request.app.state, "vision", None)
    if vision is None:
        raise RuntimeError("Los modelos de cara no están cargados: el servidor los carga al arrancar.")
    return vision


@router.post("/dispositivos/{codigo}/rostros", response_model=RespuestaRostro, operation_id="enviarRostro")
async def enviar_rostro(codigo: str, request: Request, conexion: Conexion) -> RespuestaRostro | JSONResponse:
    """Orden de las comprobaciones (decisión de B2): token (401), cámara inactiva (403), tipo (415), tamaño (413),
    ritmo (429) e imagen (422). Después del token, los errores se responden sin deshacer el último contacto."""
    inicio = time.perf_counter()
    momento = tiempo.ahora()
    camara = await run_in_threadpool(
        rostros.autenticar, conexion, codigo, request.headers.get("authorization"), momento
    )
    if not camara.activo:
        return rostros.rechazo(camara, 403, "dispositivo_inactivo", "La cámara está desactivada.")
    if not rostros.es_jpeg(request.headers.get("content-type")):
        return rostros.rechazo(camara, 415, "tipo_no_soportado", "El recorte debe ir como image/jpeg.")
    datos = await rostros.leer_cuerpo(request)
    if datos is None:
        return rostros.rechazo(camara, 413, "imagen_grande", "El recorte pasa de 100 KB (102 400 bytes).")
    if not request.app.state.ritmo.permitir(camara.codigo):
        return rostros.rechazo(
            camara,
            429,
            "demasiadas_peticiones",
            "Llegaron dos recortes con menos de 0,8 s entre sí: espera antes de enviar otro.",
            {"Retry-After": rostros.REINTENTAR_EN_S},
        )
    return await run_in_threadpool(
        rostros.procesar,
        conexion,
        camara,
        datos,
        _vision(request),
        momento,
        inicio,
        request.headers.get("x-accesia-firmware"),
    )
