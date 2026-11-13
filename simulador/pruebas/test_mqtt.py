"""
Nombre: test_mqtt.py
Descripción: Pruebas de la puerta por MQTT del simulador con un cliente paho falso y un reloj falso: «contrato MQTT · puerta», «· disponible», «· estado del simulador» y «· broker» (conexión, reintentos, sesión tomada y rechazos).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import json
import socket
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from dobles import (
    CLAVE_MQTT,
    ClienteMqttFalso,
    DetectorFalso,
    FabricaMqtt,
    Publicado,
    RelojFalso,
    ServidorFalso,
    escribir_foto,
    imagen_sintetica,
)

from simulador import FIRMWARE
from simulador.carpeta import correr_carpeta
from simulador.mqtt import Broker, PuertaMqtt, estado_camara
from simulador.recortador import RecortadorYuNet
from simulador.recorte import Cara
from simulador.ritmo import Ritmo

puerta_mqtt = pytest.mark.marca("contrato MQTT · puerta")
disponible = pytest.mark.marca("contrato MQTT · disponible")
estado = pytest.mark.marca("contrato MQTT · estado del simulador")
broker = pytest.mark.marca("contrato MQTT · broker")

DISPONIBLE = "accesia/entrada/disponible"
ESTADO = "accesia/entrada/estado"
PUERTA_SET = "accesia/entrada/puerta/set"
PUERTA_ESTADO = "accesia/entrada/puerta/estado"

ONLINE = Publicado(DISPONIBLE, "online", 1, True)
OFFLINE = Publicado(DISPONIBLE, "offline", 1, True)
ABIERTA = Publicado(PUERTA_ESTADO, "abierta", 1, True)
CERRADA = Publicado(PUERTA_ESTADO, "cerrada", 1, True)


@pytest.fixture
def lineas() -> list[str]:
    return []


Armar = Callable[..., tuple[PuertaMqtt, ClienteMqttFalso]]


@pytest.fixture
def armar(reloj: RelojFalso, lineas: list[str]) -> Armar:
    """La puerta del simulador para la cámara entrada, con el paho falso y el reloj falso."""

    def crear(segundos: int = 3, ip: str = "192.168.137.50") -> tuple[PuertaMqtt, ClienteMqttFalso]:
        fabrica = FabricaMqtt(ip=ip)
        puerta = PuertaMqtt(Broker("192.168.137.1"), "entrada", CLAVE_MQTT, segundos=segundos, reloj=reloj,
                            salida=lineas.append, crear_cliente=fabrica)
        [cliente] = fabrica.clientes
        return puerta, cliente

    return crear


def _dijo(lineas: list[str], texto: str) -> bool:
    return any(texto in linea for linea in lineas)


# --- Disponibilidad ---


@disponible
def test_se_conecta_como_la_placa_con_el_ultimo_deseo_offline(armar: Armar) -> None:
    _, cliente = armar()

    assert cliente.client_id == "entrada"  # la ACL usa %c: el código es el client id
    assert (cliente.usuario, cliente.clave) == ("camara", CLAVE_MQTT)
    assert cliente.ultimo_deseo == OFFLINE
    assert cliente.publicados == []  # nada hasta que el broker acepte la conexión


@disponible
def test_al_conectarse_publica_online_y_la_puerta_y_escucha_las_ordenes(armar: Armar) -> None:
    puerta, cliente = armar()

    cliente.conectar()

    assert puerta.conectada
    assert cliente.publicados[:2] == [ONLINE, CERRADA]
    assert cliente.suscripciones == [(PUERTA_SET, 1)]


@disponible
def test_al_salir_publica_offline_y_se_desconecta(armar: Armar, lineas: list[str]) -> None:
    puerta, cliente = armar()
    puerta.arrancar()
    cliente.conectar()

    puerta.cerrar()

    assert cliente.publicados[-1] == OFFLINE
    assert cliente.desconexiones == 1
    assert not cliente.bucle  # loop_stop: el hilo de paho termina
    assert _dijo(lineas, "Puerta desconectada del broker (offline)")


@disponible
def test_al_salir_con_la_puerta_abierta_publica_cerrada_y_despues_offline(armar: Armar, lineas: list[str]) -> None:
    puerta, cliente = armar()
    cliente.conectar()
    cliente.recibir(PUERTA_SET, b"ABRIR")

    puerta.cerrar()

    assert cliente.publicados[-2:] == [CERRADA, OFFLINE]
    assert _dijo(lineas, "Puerta cerrada al salir")


@disponible
def test_cerrar_dos_veces_publica_offline_una_vez(armar: Armar) -> None:
    puerta, cliente = armar()
    cliente.conectar()

    puerta.cerrar()
    puerta.cerrar()

    assert cliente.en(DISPONIBLE).count(OFFLINE) == 1
    assert cliente.desconexiones == 1


@disponible
def test_sin_conexion_al_salir_no_publica_y_queda_el_ultimo_deseo(armar: Armar) -> None:
    puerta, cliente = armar()
    cliente.conectar()
    cliente.cortar()

    puerta.cerrar()

    assert OFFLINE not in cliente.publicados
    assert cliente.desconexiones == 1  # saca a paho de sus reintentos


@disponible
def test_al_reconectarse_publica_online_y_la_puerta_como_este(armar: Armar, reloj: RelojFalso) -> None:
    puerta, cliente = armar()
    inicio = reloj.ahora
    cliente.conectar()
    cliente.recibir(PUERTA_SET, b"ABRIR")
    cliente.cortar()
    reloj.ahora = inicio + 3  # se cierra sola sin conexión: no se publica nada todavía
    puerta.revisar()
    antes = len(cliente.publicados)

    cliente.conectar()

    assert cliente.publicados[antes:antes + 2] == [ONLINE, CERRADA]


# --- La puerta ---


@puerta_mqtt
def test_abrir_publica_abierta_y_a_los_3_s_cerrada(armar: Armar, reloj: RelojFalso, lineas: list[str]) -> None:
    puerta, cliente = armar()
    inicio = reloj.ahora
    cliente.conectar()
    antes = len(cliente.publicados)

    cliente.recibir(PUERTA_SET, b"ABRIR")
    assert cliente.publicados[antes:] == [ABIERTA]
    assert _dijo(lineas, "PUERTA ABIERTA (3 s)")

    reloj.ahora = inicio + 2.9
    puerta.revisar()
    assert puerta.abierta and cliente.publicados[antes:] == [ABIERTA]

    reloj.ahora = inicio + 3
    puerta.revisar()
    assert not puerta.abierta
    assert cliente.publicados[antes:] == [ABIERTA, CERRADA]
    assert lineas[-1].endswith("Puerta cerrada")


@puerta_mqtt
def test_los_segundos_configurados(armar: Armar, reloj: RelojFalso, lineas: list[str]) -> None:
    puerta, cliente = armar(segundos=10)
    inicio = reloj.ahora
    cliente.conectar()
    cliente.recibir(PUERTA_SET, b"ABRIR")

    reloj.ahora = inicio + 9.9
    puerta.revisar()
    assert puerta.abierta

    reloj.ahora = inicio + 10
    puerta.revisar()
    assert cliente.publicados[-1] == CERRADA
    assert _dijo(lineas, "PUERTA ABIERTA (10 s)")


@puerta_mqtt
def test_cerrar_la_cierra_antes(armar: Armar, reloj: RelojFalso, lineas: list[str]) -> None:
    puerta, cliente = armar()
    inicio = reloj.ahora
    cliente.conectar()
    antes = len(cliente.publicados)
    cliente.recibir(PUERTA_SET, b"ABRIR")

    reloj.ahora = inicio + 1
    cliente.recibir(PUERTA_SET, b"CERRAR")
    reloj.ahora = inicio + 3
    puerta.revisar()

    assert cliente.publicados[antes:] == [ABIERTA, CERRADA]  # el cierre por tiempo ya no publica
    assert _dijo(lineas, "Puerta cerrada (CERRAR)")


@puerta_mqtt
def test_abrir_con_la_puerta_abierta_vuelve_a_contar_sin_publicar(
    armar: Armar, reloj: RelojFalso, lineas: list[str]
) -> None:
    puerta, cliente = armar()
    inicio = reloj.ahora
    cliente.conectar()
    antes = len(cliente.publicados)
    cliente.recibir(PUERTA_SET, b"ABRIR")

    reloj.ahora = inicio + 2
    cliente.recibir(PUERTA_SET, b"ABRIR")
    assert cliente.publicados[antes:] == [ABIERTA]  # igual que la placa: no publica «abierta» otra vez
    assert _dijo(lineas, "ABRIR con la puerta abierta: vuelve a contar 3 s")

    reloj.ahora = inicio + 4.9
    puerta.revisar()
    assert puerta.abierta
    reloj.ahora = inicio + 5
    puerta.revisar()
    assert cliente.publicados[antes:] == [ABIERTA, CERRADA]


@puerta_mqtt
def test_cerrar_con_la_puerta_cerrada_no_publica(armar: Armar, lineas: list[str]) -> None:
    _, cliente = armar()
    cliente.conectar()
    antes = len(cliente.publicados)

    cliente.recibir(PUERTA_SET, b"CERRAR")

    assert cliente.publicados[antes:] == []
    assert _dijo(lineas, "CERRAR con la puerta cerrada")


@puerta_mqtt
@pytest.mark.parametrize("carga", [b"abrir", b"ABRIR ", b"OPEN", b"", b"\xff\xfe" * 40])
def test_un_mensaje_que_no_es_orden_se_ignora_y_se_dice(armar: Armar, lineas: list[str], carga: bytes) -> None:
    puerta, cliente = armar()
    cliente.conectar()
    antes = len(cliente.publicados)

    cliente.recibir(PUERTA_SET, carga)

    assert not puerta.abierta
    assert cliente.publicados[antes:] == []
    assert _dijo(lineas, f"Mensaje ignorado en {PUERTA_SET}")
    assert all(len(linea) < 200 for linea in lineas)  # un mensaje largo no llena la consola


@puerta_mqtt
def test_un_mensaje_de_otro_tema_no_mueve_la_puerta(armar: Armar) -> None:
    puerta, cliente = armar()
    cliente.conectar()

    cliente.recibir("accesia/otra/puerta/set", b"ABRIR")

    assert not puerta.abierta


# --- EstadoCamara ---


@estado
def test_lleva_solo_firmware_ip_y_segundos_encendida(armar: Armar, reloj: RelojFalso) -> None:
    _, cliente = armar()
    reloj.ahora += 12  # el broker acepta la conexión 12 s después de arrancar

    cliente.conectar()

    [publicado] = cliente.en(ESTADO)
    assert (publicado.qos, publicado.retenido) == (0, True)
    # Sin perfil, rssi, psram_kb ni libre_kb (mqtt.md, EstadoCamara).
    assert json.loads(publicado.carga) == {"firmware": FIRMWARE, "ip": "192.168.137.50", "segundos_encendida": 12}


@estado
def test_firmware_es_el_texto_de_x_accesia_firmware(armar: Armar, servidor: ServidorFalso) -> None:
    servidor.cliente().enviar(b"\xff\xd8\xff\xd9", 0.9)
    [peticion] = servidor.peticiones
    _, cliente = armar()

    cliente.conectar()

    assert json.loads(cliente.en(ESTADO)[0].carga)["firmware"] == peticion.headers["X-AccesIA-Firmware"]


@estado
def test_la_ip_es_la_de_la_conexion_con_el_broker(armar: Armar) -> None:
    _, cliente = armar(ip="127.0.0.1")

    cliente.conectar()

    assert json.loads(cliente.en(ESTADO)[0].carga)["ip"] == "127.0.0.1"


@estado
def test_se_publica_cada_60_s(armar: Armar, reloj: RelojFalso) -> None:
    puerta, cliente = armar()
    inicio = reloj.ahora
    cliente.conectar()

    reloj.ahora = inicio + 59.9
    puerta.revisar()
    assert len(cliente.en(ESTADO)) == 1

    reloj.ahora = inicio + 60
    puerta.revisar()
    reloj.ahora = inicio + 120
    puerta.revisar()

    segundos = [json.loads(publicado.carga)["segundos_encendida"] for publicado in cliente.en(ESTADO)]
    assert segundos == [0, 60, 120]
    assert all((publicado.qos, publicado.retenido) == (0, True) for publicado in cliente.en(ESTADO))


@estado
def test_sin_conexion_no_se_publica(armar: Armar, reloj: RelojFalso) -> None:
    puerta, cliente = armar()

    reloj.ahora += 600
    puerta.revisar()

    assert cliente.publicados == []


@estado
def test_el_mensaje_es_json_compacto() -> None:
    assert estado_camara("10.0.0.5", 7) == f'{{"firmware":"{FIRMWARE}","ip":"10.0.0.5","segundos_encendida":7}}'


# --- Conexión con el broker ---


@broker
def test_arrancar_no_espera_al_broker_y_reintenta_a_1_2_4_8_y_10_s(armar: Armar) -> None:
    puerta, cliente = armar()

    puerta.arrancar()

    assert cliente.conexion == ("192.168.137.1", 1883, 30)  # keepalive de 30 s, como la placa
    assert cliente.bucle  # paho corre y reintenta en su hilo
    assert cliente.esperas == (1, 10)
    puerta.cerrar()


@broker
def test_sin_broker_avisa_una_vez_y_sigue_reintentando(armar: Armar, lineas: list[str]) -> None:
    puerta, cliente = armar()

    for _ in range(3):
        cliente.fallar_conexion()

    assert sum("Sin conexión con el broker 192.168.137.1:1883" in linea for linea in lineas) == 1
    assert cliente.desconexiones == 0 and not puerta.detenida


@broker
def test_si_se_pierde_la_conexion_lo_dice_y_paho_reintenta(armar: Armar, lineas: list[str]) -> None:
    puerta, cliente = armar()
    cliente.conectar()

    cliente.cortar()

    assert not puerta.conectada and not puerta.detenida
    assert cliente.desconexiones == 0
    assert _dijo(lineas, "Se perdió la conexión con el broker")


@broker
def test_con_sesion_tomada_le_deja_la_puerta_y_no_se_reconecta(armar: Armar, lineas: list[str]) -> None:
    puerta, cliente = armar()
    cliente.conectar()

    cliente.cortar(0x8E, desde_broker=True)

    assert puerta.detenida and not puerta.conectada
    assert cliente.desconexiones == 1  # disconnect() saca a paho de su ciclo de reconexión
    assert _dijo(lineas, "sesión tomada")
    antes = len(cliente.publicados)
    puerta.cerrar()
    assert cliente.publicados[antes:] == []  # la puerta ya es de la otra cámara: no publica nada al salir


@broker
@pytest.mark.parametrize("codigo", [0x85, 0x86, 0x87])
def test_si_el_broker_rechaza_la_clave_no_reintenta(armar: Armar, lineas: list[str], codigo: int) -> None:
    puerta, cliente = armar()

    cliente.conectar(codigo)

    assert puerta.detenida
    assert cliente.desconexiones == 1
    assert cliente.publicados == []
    assert _dijo(lineas, "$env:MQTT_CAMARA_CLAVE")
    assert not _dijo(lineas, CLAVE_MQTT)


@broker
def test_si_el_broker_no_esta_disponible_sigue_reintentando(armar: Armar, lineas: list[str]) -> None:
    puerta, cliente = armar()

    cliente.conectar(0x88)  # «Server unavailable»

    assert not puerta.detenida
    assert cliente.desconexiones == 0
    assert _dijo(lineas, "reintento solo")


@broker
def test_con_el_broker_caido_los_recortes_siguen(tmp_path: Path, servidor: ServidorFalso) -> None:
    """Con paho de verdad y un puerto sin broker: arrancar no espera y el modo carpeta envía todo."""
    with socket.socket() as libre:
        libre.bind(("127.0.0.1", 0))
        puerto = libre.getsockname()[1]
    for numero in range(3):
        escribir_foto(tmp_path / f"foto-{numero}.jpg", imagen_sintetica(640, 480, numero))
    lineas: list[str] = []
    puerta = PuertaMqtt(Broker("127.0.0.1", puerto), "entrada", CLAVE_MQTT, salida=lineas.append)

    inicio = time.monotonic()
    puerta.arrancar()
    assert time.monotonic() - inicio < 1

    try:
        codigo = correr_carpeta(tmp_path, RecortadorYuNet(DetectorFalso([Cara(100, 60, 90, 110)])),
                                servidor.cliente(), Ritmo(), modo_camara=False, dormir=lambda _: None,
                                salida=lineas.append)
        assert codigo == 0
        assert len(servidor.peticiones) == 3
        limite = time.monotonic() + 15  # en Windows, una conexión rechazada tarda unos 2 s en fallar
        while not _dijo(lineas, "Sin conexión con el broker") and time.monotonic() < limite:
            time.sleep(0.05)
        assert _dijo(lineas, "Sin conexión con el broker 127.0.0.1")
        assert not puerta.conectada
    finally:
        puerta.cerrar()
