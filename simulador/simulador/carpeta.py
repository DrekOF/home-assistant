"""
Nombre: carpeta.py
Descripción: Modo carpeta, para pruebas repetibles: envía cada foto en orden por nombre, con las esperas de la cámara, y la compara con esperado.json.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Códigos de salida: 0 sin diferencias (o sin esperado.json), 1 con alguna diferencia, 2 si no se pudo probar
(carpeta sin fotos, esperado.json mal escrito o el servidor rechazó el token).
"""

import time
from collections.abc import Callable
from pathlib import Path

from simulador.consola import contar, linea_respuesta
from simulador.envio import ClienteCamara
from simulador.esperado import ARCHIVO_ESPERADO, ErrorEsperado, Obtenido, cargar_esperado, resumir
from simulador.imagen import leer_foto, preparar
from simulador.recortador import Recortador, SinEnvio
from simulador.ritmo import Ritmo

EXTENSIONES = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})


def fotos_de(carpeta: Path) -> list[Path]:
    """Las fotos de la carpeta (sin subcarpetas), en orden por nombre."""
    fotos = (ruta for ruta in carpeta.iterdir() if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES)
    return sorted(fotos, key=lambda ruta: (ruta.name.casefold(), ruta.name))


def correr_carpeta(
    carpeta: Path,
    recortador: Recortador,
    cliente: ClienteCamara,
    ritmo: Ritmo,
    *,
    modo_camara: bool,
    dormir: Callable[[float], None] = time.sleep,
    salida: Callable[[str], None] = print,
) -> int:
    try:
        esperado = cargar_esperado(carpeta)
    except ErrorEsperado as error:
        salida(str(error))
        return 2

    fotos = fotos_de(carpeta)
    if not fotos:
        salida(f"{carpeta} no tiene fotos ({', '.join(sorted(EXTENSIONES))}).")
        return 2

    obtenidos: dict[str, Obtenido] = {}
    for foto in fotos:
        imagen = leer_foto(foto)
        if imagen is None:
            obtenidos[foto.name] = Obtenido(False, nota="no se pudo leer la foto")
            salida(f"{foto.name}: no se pudo leer la foto")
            continue

        resultado = recortador.procesar(preparar(imagen, modo_camara))
        if isinstance(resultado, SinEnvio):
            obtenidos[foto.name] = Obtenido(False, nota=resultado.detalle)
            salida(f"{foto.name}: no se envía, {resultado.detalle}")
            continue

        dormir(ritmo.falta())
        respuesta = cliente.enviar(resultado.jpeg, resultado.puntaje)
        espera = ritmo.registrar(respuesta)
        obtenidos[foto.name] = Obtenido(True, respuesta)
        salida(f"{foto.name}: {linea_respuesta(respuesta, espera)}")

        if respuesta.estado in (401, 403):
            # Con el mismo token, las demás fotos recibirían lo mismo cada 30 s.
            salida("El servidor no acepta la cámara: revisa $env:TOKEN_CAMARA y --codigo. Se detiene aquí.")
            return 2

    if esperado is None:
        cuantas = contar(len(fotos), "foto", "fotos")
        salida(f"Listo: {cuantas}. La carpeta no trae {ARCHIVO_ESPERADO}: no se comparó nada.")
        return 0
    return 1 if resumir(esperado, obtenidos, salida) else 0
