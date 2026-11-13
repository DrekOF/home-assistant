"""
Nombre: comandos.py
Descripción: Comando accesia del servidor: crear-camara registra una cámara y muestra su token una sola vez, sin pasar por la web (RF-10 · C5); descargar-modelos baja YuNet y SFace y comprueba su SHA-256; mcp arranca el servidor MCP del agente y semilla agente crea los datos de su evaluación.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from accesia import camaras, db, modelos, semilla
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
    descarga = comandos.add_parser(
        "descargar-modelos",
        help="descarga YuNet y SFace de opencv_zoo y comprueba su SHA-256",
        description="Descarga los modelos de cara del commit fijo de opencv_zoo a datos/modelos/ y comprueba su SHA-256. "
        "Lo que ya está y coincide no se vuelve a bajar.",
    )
    descarga.add_argument("--carpeta", type=Path, default=None, help="por defecto, datos/modelos/ del repositorio")
    comandos.add_parser(
        "mcp",
        help="arranca el servidor MCP del agente en el puerto 8001",
        description="Arranca el servidor MCP «AccesIA» (contratos/mcp-agente.md) en http://0.0.0.0:8001/mcp. Solo se "
        "conecta a la base con el usuario agente (D-15). Lo usa el servicio mcp de Docker Compose.",
    )
    sembrar_ = comandos.add_parser(
        "semilla",
        help="crea los datos de la evaluación del agente",
        description="Crea los datos de la evaluación de contratos/mcp-agente.md con fechas relativas a hoy, en hora de "
        "Colombia, y revisa las preguntas 1 a 9 con las herramientas. Volver a correrla reemplaza solo lo suyo.",
    )
    sembrar_.add_argument("conjunto", choices=["agente"], help="agente: los datos de la evaluación del agente")
    sembrar_.add_argument(
        "--con-datos-reales",
        action="store_true",
        help="la agrega aunque la base ya tenga personas o eventos que no son suyos (por ejemplo, del Hito 1); "
        "nunca los cambia",
    )
    sembrar_.add_argument("--borrar", action="store_true", help="borra solo lo que creó la semilla")
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


def descargar_modelos(argumentos: argparse.Namespace) -> int:
    try:
        modelos.descargar(argumentos.carpeta)
    except (OSError, RuntimeError) as error:
        print(f"No se pudieron descargar los modelos: {error}", file=sys.stderr)
        return 1
    return 0


def sembrar(argumentos: argparse.Namespace) -> int:
    """accesia semilla agente: crea, reemplaza o borra solo los datos de la semilla, en una transacción."""
    try:
        with db.transaccion() as conexion:
            if argumentos.borrar:
                lineas = semilla.describir_borrado(semilla.borrar(conexion))
            else:
                lineas = semilla.describir(semilla.crear(conexion, con_datos_reales=argumentos.con_datos_reales))
    except semilla.ErrorDeSemilla as error:
        print(error, file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        print(
            f"No se pudo escribir la semilla en la base ({type(error).__name__}). Córrela en el servicio servidor, que "
            "usa el dueño de la base: docker compose -f infra/compose.yaml exec servidor accesia semilla agente",
            file=sys.stderr,
        )
        return 1
    for linea in lineas:
        print(linea)
    return 0


def principal(argumentos: Sequence[str] | None = None) -> int:
    """Punto de entrada del comando accesia (pyproject.toml, [project.scripts])."""
    leidos = _lector().parse_args(argumentos)
    if leidos.comando == "crear-camara":
        return crear_camara(leidos)
    if leidos.comando == "descargar-modelos":
        return descargar_modelos(leidos)
    if leidos.comando == "mcp":
        from accesia import servidor_mcp  # solo aquí: trae el SDK de MCP y uvicorn

        return servidor_mcp.correr()
    if leidos.comando == "semilla":
        return sembrar(leidos)
    return 2


if __name__ == "__main__":
    sys.exit(principal())
