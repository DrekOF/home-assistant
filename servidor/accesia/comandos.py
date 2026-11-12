"""
Nombre: comandos.py
Descripción: Comando accesia del servidor: crear-camara registra una cámara y muestra su token una sola vez, sin pasar por la web (RF-10 · C5).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import argparse
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from accesia import camaras, db
from accesia.errores import ErrorAccesIA
from accesia.esquemas import DispositivoNuevo

TIPOS = ("tinyml", "respaldo", "simulador")

# Lo que debe tener cada campo, para explicar un error de validación en español.
REGLAS = {
    "codigo": "El código debe tener de 3 a 32 letras minúsculas, números o guiones (por ejemplo, entrada).",
    "nombre": "El nombre debe tener de 2 a 60 caracteres.",
}


def _lector() -> argparse.ArgumentParser:
    lector = argparse.ArgumentParser(prog="accesia", description="Comandos del servidor de AccesIA.")
    comandos = lector.add_subparsers(dest="comando", required=True, metavar="comando")
    camara = comandos.add_parser(
        "crear-camara",
        help="registra una cámara y muestra su token una sola vez",
        description="Registra una cámara y muestra su token una sola vez (RF-10 · C5). La base guarda solo su hash.",
    )
    camara.add_argument("codigo", help="código de la cámara, por ejemplo entrada")
    camara.add_argument("--nombre", required=True, help="nombre para mostrar, por ejemplo Entrada")
    camara.add_argument("--tipo", required=True, choices=TIPOS, help="tinyml, respaldo o simulador")
    camara.add_argument("--url-captura", help="URL de captura; obligatoria para el tipo respaldo")
    return lector


def _explicar(error: ValidationError) -> list[str]:
    mensajes: dict[str, None] = {}
    for detalle in error.errors():
        campo = str(detalle["loc"][0]) if detalle.get("loc") else ""
        if detalle.get("type") == "value_error":
            mensajes[str(detalle["msg"]).removeprefix("Value error, ")] = None
        else:
            mensajes[REGLAS.get(campo, f"Revisa «{campo}».")] = None
    return list(mensajes)


def crear_camara(argumentos: argparse.Namespace) -> int:
    try:
        datos = DispositivoNuevo(
            codigo=argumentos.codigo, nombre=argumentos.nombre, tipo=argumentos.tipo, url_captura=argumentos.url_captura
        )
    except ValidationError as error:
        for mensaje in _explicar(error):
            print(mensaje, file=sys.stderr)
        return 1
    try:
        with db.transaccion() as conexion:
            camara = camaras.crear(conexion, datos)
    except ErrorAccesIA as error:
        print(error.detalle, file=sys.stderr)
        return 1
    print(f"Cámara «{camara.codigo}» creada: {camara.nombre}, tipo {camara.tipo}.")
    print("Este es su token. Se muestra solo esta vez: cópialo ahora (la base guarda solo su hash).")
    print(camara.token)
    return 0


def principal(argumentos: Sequence[str] | None = None) -> int:
    """Punto de entrada del comando accesia (pyproject.toml, [project.scripts])."""
    leidos = _lector().parse_args(argumentos)
    if leidos.comando == "crear-camara":
        return crear_camara(leidos)
    return 2


if __name__ == "__main__":
    sys.exit(principal())
