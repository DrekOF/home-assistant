"""
Nombre: comandos.py
Descripción: El comando simulador: modos webcam y carpeta, con la puerta por MQTT si se pide con --puerta, y modelo para descargar YuNet antes de clase.
Fecha de creación: 2026-11-12
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.2

    uv run simulador webcam --codigo entrada [--como-camara] [--camara 0] [--puerta]
    uv run simulador carpeta datos/prueba --codigo entrada [--como-camara] [--puerta]
    uv run simulador modelo

El token de la cámara sale de la variable TOKEN_CAMARA y, con --puerta, la clave del usuario camara del broker sale
de MQTT_CAMARA_CLAVE: ninguno va en un archivo, en una opción ni en la salida.
"""

import argparse
import os
import sys
from pathlib import Path

from simulador import FIRMWARE
from simulador.carpeta import correr_carpeta
from simulador.consola import preparar_salida
from simulador.deteccion import PUNTAJE_MIN, DetectorYuNet
from simulador.envio import ClienteCamara
from simulador.modelo import YUNET_SHA256, ErrorModelo, asegurar_modelo
from simulador.mqtt import (BROKER, BROKER_DE_LA_PI, IP_DE_LA_PI, VARIABLE_CLAVE, Broker, PuertaMqtt, codigo_valido,
                            leer_broker)
from simulador.puerta import SEGUNDOS_MAX, SEGUNDOS_MIN, SEGUNDOS_POR_DEFECTO
from simulador.recortador import CARA_MIN, RecortadorYuNet
from simulador.ritmo import Ritmo
from simulador.rutas import resolver_carpeta
from simulador.webcam import correr_webcam

SERVIDOR = "http://localhost:8000"
SERVIDOR_DE_LA_PI = f"http://{IP_DE_LA_PI}:8000"  # el de la demo (D-22)
# Carga la clave desde infra/.env sin mostrarla y sin que quede en el historial (desde simulador/).
CARGAR_CLAVE = (
    f"$env:{VARIABLE_CLAVE} = (Select-String -Path ..\\infra\\.env "
    f"-Pattern '^{VARIABLE_CLAVE}=(.+)$').Matches[0].Groups[1].Value"
)


def _puntaje(texto: str) -> float:
    valor = float(texto.replace(",", "."))
    if not 0 < valor <= 1:
        raise argparse.ArgumentTypeError("debe estar entre 0 y 1")
    return valor


def _pixeles(texto: str) -> int:
    valor = int(texto)
    if valor < 0:
        raise argparse.ArgumentTypeError("no puede ser negativo")
    return valor


def _segundos_puerta(texto: str) -> int:
    try:
        valor = int(texto)
    except ValueError:
        raise argparse.ArgumentTypeError("debe ser un número entero de segundos") from None
    if not SEGUNDOS_MIN <= valor <= SEGUNDOS_MAX:
        raise argparse.ArgumentTypeError(f"debe estar entre {SEGUNDOS_MIN} y {SEGUNDOS_MAX}")
    return valor


def _broker(texto: str) -> Broker:
    try:
        return leer_broker(texto)
    except ValueError as error:  # el mensaje nunca repite el texto, por si trae una clave
        raise argparse.ArgumentTypeError(str(error)) from None


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simulador",
        description="Simulador de la cámara de AccesIA: detecta con YuNet, recorta con la fórmula del contrato "
        "y envía cada recorte al servidor. El token sale de la variable TOKEN_CAMARA.",
    )
    parser.add_argument("--version", action="version", version=FIRMWARE)
    modos = parser.add_subparsers(dest="modo", required=True, metavar="{webcam,carpeta,modelo}")

    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--codigo", required=True, help="código de la cámara en el servidor, por ejemplo entrada")
    comunes.add_argument("--servidor", default=SERVIDOR, help=f"dirección del servidor (por defecto {SERVIDOR}; en la Pi, {SERVIDOR_DE_LA_PI})")
    comunes.add_argument(
        "--como-camara",
        action="store_true",
        help="antes de detectar, deja la imagen como la del ESP32-S3: 4:3 al centro, 320 × 240 y JPEG 80",
    )
    comunes.add_argument(
        "--cara-min",
        type=_pixeles,
        default=CARA_MIN,
        help=f"no envía caras de menos píxeles de alto (por defecto {CARA_MIN}, igual que CARA_MIN_PX)",
    )
    comunes.add_argument(
        "--puntaje-min",
        type=_puntaje,
        default=PUNTAJE_MIN,
        help=f"puntaje mínimo de YuNet (por defecto {PUNTAJE_MIN}, el del paso 1 de R7)",
    )
    comunes.add_argument(
        "--puerta",
        action="store_true",
        help="también hace la parte MQTT de la cámara: recibe ABRIR y CERRAR y publica la puerta, su estado y su "
        "disponibilidad. Apagada por defecto, para no quitarle el código a la placa. La clave del usuario camara "
        f"sale de la variable {VARIABLE_CLAVE}",
    )
    comunes.add_argument(
        "--broker",
        type=_broker,
        default=None,
        help=f"broker de la puerta (por defecto {BROKER}; en la Pi, {BROKER_DE_LA_PI})",
    )
    comunes.add_argument(
        "--puerta-segundos",
        type=_segundos_puerta,
        default=None,
        help=f"segundos que la puerta queda abierta con ABRIR (por defecto {SEGUNDOS_POR_DEFECTO}, "
        f"de {SEGUNDOS_MIN} a {SEGUNDOS_MAX})",
    )

    webcam = modos.add_parser("webcam", parents=[comunes], help="detecta y envía con la webcam")
    webcam.add_argument("--camara", type=int, default=0, help="número de la webcam (por defecto 0, la primera)")

    carpeta = modos.add_parser(
        "carpeta", parents=[comunes], help="envía las fotos de una carpeta y las compara con su esperado.json"
    )
    carpeta.add_argument("carpeta", type=Path, help="carpeta con las fotos, por ejemplo datos/prueba")

    modos.add_parser("modelo", help="descarga YuNet a datos/modelos/ y comprueba su SHA-256")
    return parser


def principal(argv: list[str] | None = None) -> int:
    preparar_salida()
    args = construir_parser().parse_args(argv)
    try:
        return _correr(args)
    except KeyboardInterrupt:
        return 130


def _correr(args: argparse.Namespace) -> int:
    if args.modo == "modelo":
        try:
            ruta = asegurar_modelo()
        except ErrorModelo as error:
            print(error, file=sys.stderr)
            return 2
        print(f"Modelo listo: {ruta} (SHA-256 {YUNET_SHA256})")
        return 0

    token = os.environ.get("TOKEN_CAMARA", "").strip()
    if not token:
        print('Falta el token de la cámara. En PowerShell: $env:TOKEN_CAMARA = "<token>"', file=sys.stderr)
        return 2
    if not args.servidor.startswith(("http://", "https://")):
        print(f"--servidor debe empezar por http:// o https:// (llegó {args.servidor})", file=sys.stderr)
        return 2
    if args.modo == "carpeta":
        carpeta = resolver_carpeta(args.carpeta)
        if not carpeta.is_dir():
            print(f"No existe la carpeta {args.carpeta}", file=sys.stderr)
            return 2

    clave_mqtt = ""
    if args.puerta:
        if not codigo_valido(args.codigo):
            print("Con --puerta, --codigo es el client id y va en los temas: de 3 a 32 minúsculas, números o "
                  "guiones, y no puede ser servidor.", file=sys.stderr)
            return 2
        clave_mqtt = os.environ.get(VARIABLE_CLAVE, "").strip()
        if not clave_mqtt:
            print(f"Falta la clave del usuario camara del broker. Desde simulador/, en PowerShell: {CARGAR_CLAVE}",
                  file=sys.stderr)
            return 2
    elif args.broker is not None or args.puerta_segundos is not None:
        print("--broker y --puerta-segundos solo sirven con --puerta.", file=sys.stderr)
        return 2

    try:
        modelo = asegurar_modelo()
    except ErrorModelo as error:
        print(error, file=sys.stderr)
        return 2

    recortador = RecortadorYuNet(DetectorYuNet(modelo, args.puntaje_min), args.cara_min)
    cliente = ClienteCamara(args.servidor, args.codigo, token)
    ritmo = Ritmo()
    # Sin --puerta no se crea el cliente MQTT: el simulador no se conecta y la placa conserva su código.
    puerta = None
    if args.puerta:
        puerta = PuertaMqtt(args.broker or leer_broker(BROKER), args.codigo, clave_mqtt,
                            segundos=args.puerta_segundos or SEGUNDOS_POR_DEFECTO)
        puerta.arrancar()
    try:
        if args.modo == "webcam":
            return correr_webcam(recortador, cliente, ritmo, modo_camara=args.como_camara, indice=args.camara,
                                 puerta=puerta)
        return correr_carpeta(carpeta, recortador, cliente, ritmo, modo_camara=args.como_camara)
    finally:
        if puerta is not None:
            puerta.cerrar()
        cliente.cerrar()


if __name__ == "__main__":
    sys.exit(principal())
