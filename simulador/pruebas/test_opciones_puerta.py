"""
Nombre: test_opciones_puerta.py
Descripción: Prueba «contrato MQTT · broker» de las opciones del comando: sin --puerta no se crea el cliente MQTT (la placa conserva su código), y con --puerta se valida el código, la clave y el broker antes de conectarse.
Fecha de creación: 2026-11-12
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.1
"""

from pathlib import Path
from typing import Any

import pytest
from dobles import CLAVE_MQTT, TOKEN, Publicado, ServidorFalso, escribir_foto, imagen_sintetica, preparar_principal

import simulador.comandos as comandos
from simulador.comandos import construir_parser, principal
from simulador.mqtt import (BROKER_DE_LA_PI, FORMA_BROKER, IP_DE_LA_PI, Broker, PuertaMqtt, codigo_valido,
                            leer_broker)
from simulador.recorte import Cara

pytestmark = pytest.mark.marca("contrato MQTT · broker")

CARA = Cara(100, 60, 90, 110)


@pytest.fixture
def fotos(tmp_path: Path) -> Path:
    carpeta = tmp_path / "fotos"
    carpeta.mkdir()
    for numero in range(2):
        escribir_foto(carpeta / f"foto-{numero}.jpg", imagen_sintetica(640, 480, numero))
    return carpeta


def test_sin_puerta_no_se_crea_el_cliente_mqtt(
    monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, fotos: Path
) -> None:
    """C2: sin --puerta el simulador no se conecta al broker y la placa conserva la puerta de su código."""
    creados = preparar_principal(monkeypatch, servidor, [CARA])

    assert principal(["carpeta", str(fotos), "--codigo", "entrada"]) == 0

    assert creados == []
    assert len(servidor.peticiones) == 2  # los recortes sí se enviaron


def test_con_puerta_se_conecta_y_al_terminar_publica_offline(
    monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, fotos: Path, capsys: pytest.CaptureFixture
) -> None:
    creados = preparar_principal(monkeypatch, servidor, [CARA])

    assert principal(["carpeta", str(fotos), "--codigo", "entrada", "--puerta"]) == 0

    [cliente] = creados
    assert cliente.client_id == "entrada"
    assert cliente.conexion == ("127.0.0.1", 1883, 30)
    assert cliente.publicados[0] == Publicado("accesia/entrada/disponible", "online", 1, True)
    assert cliente.publicados[-1] == Publicado("accesia/entrada/disponible", "offline", 1, True)
    assert cliente.desconexiones == 1
    assert len(servidor.peticiones) == 2
    salida = capsys.readouterr()
    assert CLAVE_MQTT not in salida.out + salida.err
    assert TOKEN not in salida.out + salida.err


def test_broker_y_segundos_llegan_a_la_puerta(
    monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, fotos: Path
) -> None:
    creados = preparar_principal(monkeypatch, servidor)
    puertas: list[dict[str, Any]] = []

    def crear_puerta(*args: Any, **kwargs: Any) -> PuertaMqtt:
        puertas.append(kwargs)
        return PuertaMqtt(*args, **kwargs)

    monkeypatch.setattr(comandos, "PuertaMqtt", crear_puerta)

    codigo = principal(["carpeta", str(fotos), "--codigo", "entrada", "--puerta", "--broker",
                        "mqtt://192.168.137.1:1884", "--puerta-segundos", "5"])

    assert codigo == 0
    assert creados[0].conexion == ("192.168.137.1", 1884, 30)
    assert puertas == [{"segundos": 5}]


def test_con_puerta_y_sin_la_clave_sale_con_2_sin_conectarse(
    monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, fotos: Path, capsys: pytest.CaptureFixture
) -> None:
    creados = preparar_principal(monkeypatch, servidor, [CARA])
    monkeypatch.delenv("MQTT_CAMARA_CLAVE")

    assert principal(["carpeta", str(fotos), "--codigo", "entrada", "--puerta"]) == 2

    assert creados == []
    assert servidor.peticiones == []
    error = capsys.readouterr().err
    assert "MQTT_CAMARA_CLAVE" in error
    assert "Select-String" in error  # dice cómo cargarla desde infra/.env sin mostrarla


@pytest.mark.parametrize("codigo", ["servidor", "en", "Entrada", "entrada_1", "entrada/1", "entrada#", "a" * 33])
def test_con_puerta_el_codigo_debe_servir_de_client_id(
    monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, fotos: Path, codigo: str
) -> None:
    creados = preparar_principal(monkeypatch, servidor, [CARA])

    assert principal(["carpeta", str(fotos), "--codigo", codigo, "--puerta"]) == 2

    assert creados == []
    assert servidor.peticiones == []


@pytest.mark.parametrize("opciones", [["--broker", "mqtt://localhost:1883"], ["--puerta-segundos", "5"]])
def test_broker_y_segundos_sin_puerta_salen_con_2(
    monkeypatch: pytest.MonkeyPatch, servidor: ServidorFalso, fotos: Path, capsys: pytest.CaptureFixture,
    opciones: list[str],
) -> None:
    creados = preparar_principal(monkeypatch, servidor, [CARA])

    assert principal(["carpeta", str(fotos), "--codigo", "entrada", *opciones]) == 2

    assert creados == []
    assert "solo sirven con --puerta" in capsys.readouterr().err


@pytest.mark.parametrize("valor", ["0", "61", "tres", "2.5"])
def test_puerta_segundos_de_1_a_60(valor: str) -> None:
    with pytest.raises(SystemExit) as salida:
        construir_parser().parse_args(["carpeta", "x", "--codigo", "entrada", "--puerta", "--puerta-segundos", valor])
    assert salida.value.code == 2


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("mqtt://localhost", Broker("localhost", 1883)),
        ("mqtt://192.168.137.1:1883", Broker("192.168.137.1", 1883)),
        ("mqtt://192.168.137.1:1884/", Broker("192.168.137.1", 1884)),
        ("MQTT://Broker.Local", Broker("broker.local", 1883)),
    ],
)
def test_broker_bien_escrito(texto: str, esperado: Broker) -> None:
    assert leer_broker(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    ["http://localhost:1883", "localhost:1883", "mqtts://localhost", "mqtt://", "mqtt://localhost:1883/algo",
     "mqtt://localhost:99999", "mqtt://localhost:0", "mqtt://localhost:uno"],
)
def test_broker_mal_escrito(texto: str) -> None:
    with pytest.raises(ValueError, match="mqtt://servidor:puerto"):
        leer_broker(texto)


def test_broker_con_clave_no_la_repite(capsys: pytest.CaptureFixture) -> None:
    """La clave nunca va en la línea de comandos; si alguien la escribe ahí, el error no la repite."""
    with pytest.raises(SystemExit):
        construir_parser().parse_args(["carpeta", "x", "--codigo", "entrada", "--puerta", "--broker",
                                       f"mqtt://camara:{CLAVE_MQTT}@localhost:1883"])

    error = capsys.readouterr().err
    assert CLAVE_MQTT not in error
    assert "$env:MQTT_CAMARA_CLAVE" in error


@pytest.mark.parametrize(("codigo", "valido"), [
    ("entrada", True), ("lab-2", True), ("abc", True), ("a" * 32, True),
    ("servidor", False), ("ab", False), ("a" * 33, False), ("Entrada", False), ("entrada_1", False), ("", False),
])
def test_codigo_como_en_openapi_y_la_placa(codigo: str, valido: bool) -> None:
    """^[a-z0-9-]{3,32}$ y distinto de «servidor», como openapi.yaml y codigo_valido de la placa."""
    assert codigo_valido(codigo) is valido


@pytest.mark.marca("D-22 · IP de la Pi")
def test_los_ejemplos_de_la_pi_son_validos_y_salen_de_un_solo_lugar() -> None:
    assert leer_broker(BROKER_DE_LA_PI) == Broker(IP_DE_LA_PI, 1883)
    assert IP_DE_LA_PI in FORMA_BROKER
    assert comandos.SERVIDOR_DE_LA_PI == f"http://{IP_DE_LA_PI}:8000"
    assert IP_DE_LA_PI != "192.168.137.1"  # el portátil, que con D-22 solo es el plan B
