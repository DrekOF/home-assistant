"""
Nombre: test_puerta.py
Descripción: Prueba «contrato MQTT · puerta» de la lógica pura de la puerta (igual que PuertaLogica de la placa) y de la franja «PUERTA ABIERTA» de la ventana de la webcam.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import numpy as np
import pytest
from dobles import (
    CLAVE_MQTT,
    CapturaFalsa,
    DetectorFalso,
    FabricaMqtt,
    RelojFalso,
    ServidorFalso,
    VentanaFalsa,
    imagen_sintetica,
)

from simulador.mqtt import Broker, PuertaMqtt
from simulador.puerta import ABIERTA, CERRADA, SEGUNDOS_POR_DEFECTO, Orden, Puerta, leer_orden
from simulador.recortador import RecortadorYuNet, SinEnvio
from simulador.ritmo import Ritmo
from simulador.webcam import ALTO_FRANJA, VERDE, correr_webcam, dibujar

pytestmark = pytest.mark.marca("contrato MQTT · puerta")

INICIO = 1000.0


# --- Órdenes ---


def test_abrir_y_cerrar_exactos_son_ordenes() -> None:
    assert leer_orden(b"ABRIR") is Orden.ABRIR
    assert leer_orden(b"CERRAR") is Orden.CERRAR


@pytest.mark.parametrize(
    "carga",
    [b"abrir", b"Abrir", b"ABRIR ", b" ABRIR", b"ABRIR\n", b"cerrar", b'"ABRIR"', b"ABRIRCERRAR", b"OPEN", b"",
     b"\xff\xfe"],
)
def test_lo_demas_no_es_una_orden(carga: bytes) -> None:
    """Como leer_orden de la placa: nada de mayúsculas a medias, espacios ni comillas."""
    assert leer_orden(carga) is None


# --- La puerta ---


def test_por_defecto_queda_abierta_3_s() -> None:
    assert SEGUNDOS_POR_DEFECTO == 3
    assert Puerta().segundos == 3


def test_empieza_cerrada() -> None:
    puerta = Puerta()
    assert not puerta.abierta
    assert puerta.estado == CERRADA


def test_abrir_la_abre_los_segundos_configurados() -> None:
    puerta = Puerta(3)

    assert puerta.orden(Orden.ABRIR, INICIO)  # cambió: se publica «abierta»
    assert puerta.estado == ABIERTA
    assert not puerta.actualizar(INICIO + 2.999)
    assert puerta.actualizar(INICIO + 3)  # cambió: se publica «cerrada»
    assert puerta.estado == CERRADA
    assert not puerta.actualizar(INICIO + 100)  # ya estaba cerrada: no se publica otra vez


@pytest.mark.parametrize("segundos", [1, 10, 60])
def test_los_segundos_se_configuran(segundos: int) -> None:
    puerta = Puerta(segundos)
    puerta.orden(Orden.ABRIR, INICIO)

    assert not puerta.actualizar(INICIO + segundos - 0.001)
    assert puerta.actualizar(INICIO + segundos)


def test_cerrar_la_cierra_antes() -> None:
    puerta = Puerta(3)
    puerta.orden(Orden.ABRIR, INICIO)

    assert puerta.orden(Orden.CERRAR, INICIO + 1)
    assert puerta.estado == CERRADA
    assert not puerta.actualizar(INICIO + 3)  # el cierre por tiempo ya no publica nada


def test_abrir_con_la_puerta_abierta_vuelve_a_contar_sin_cambiar() -> None:
    puerta = Puerta(3)
    puerta.orden(Orden.ABRIR, INICIO)

    assert not puerta.orden(Orden.ABRIR, INICIO + 2)  # no cambió: no se publica «abierta» otra vez
    assert not puerta.actualizar(INICIO + 4.999)
    assert puerta.actualizar(INICIO + 5)


def test_cerrar_con_la_puerta_cerrada_no_cambia() -> None:
    assert not Puerta(3).orden(Orden.CERRAR, INICIO)


def test_faltan() -> None:
    puerta = Puerta(3)
    assert puerta.faltan(INICIO) == 0

    puerta.orden(Orden.ABRIR, INICIO)

    assert puerta.faltan(INICIO + 1.5) == pytest.approx(1.5)
    assert puerta.faltan(INICIO + 10) == 0


# --- Cómo se ve en la ventana de la webcam ---


def _es_verde(pixel: np.ndarray) -> bool:
    return tuple(int(canal) for canal in pixel) == VERDE


def test_la_franja_sale_arriba_solo_con_aviso() -> None:
    imagen = imagen_sintetica(640, 480)
    resultado = SinEnvio("sin_cara", "Sin cara")

    con_aviso = dibujar(imagen, resultado, "Esperando una cara", "PUERTA ABIERTA (3 s)")
    sin_aviso = dibujar(imagen, resultado, "Esperando una cara")

    assert _es_verde(con_aviso[2, 2]) and _es_verde(con_aviso[ALTO_FRANJA - 2, con_aviso.shape[1] - 3])
    assert not _es_verde(con_aviso[ALTO_FRANJA + 5, 2])  # debajo de la franja sigue la imagen
    assert not _es_verde(sin_aviso[2, 2])
    # El texto va en negro sobre la franja.
    assert (con_aviso[:ALTO_FRANJA, :300] == 0).all(axis=2).any()


def test_el_aviso_cuenta_los_segundos_que_faltan() -> None:
    reloj = RelojFalso(INICIO)
    fabrica = FabricaMqtt()
    puerta = PuertaMqtt(Broker("localhost"), "entrada", CLAVE_MQTT, segundos=3, reloj=reloj, salida=lambda _: None,
                        crear_cliente=fabrica)
    [cliente] = fabrica.clientes
    cliente.conectar()
    assert puerta.aviso() is None

    cliente.recibir("accesia/entrada/puerta/set", b"ABRIR")
    assert puerta.aviso() == "PUERTA ABIERTA (3 s)"
    reloj.ahora = INICIO + 1
    assert puerta.aviso() == "PUERTA ABIERTA (2 s)"
    reloj.ahora = INICIO + 2.5
    assert puerta.aviso() == "PUERTA ABIERTA (1 s)"
    reloj.ahora = INICIO + 3
    puerta.revisar()
    assert puerta.aviso() is None


def test_la_ventana_muestra_puerta_abierta_mientras_esta_abierta(servidor: ServidorFalso) -> None:
    fabrica = FabricaMqtt()
    puerta = PuertaMqtt(Broker("localhost"), "entrada", CLAVE_MQTT, reloj=RelojFalso(INICIO), salida=lambda _: None,
                        crear_cliente=fabrica)
    [cliente] = fabrica.clientes
    cliente.conectar()
    cuadros = [imagen_sintetica(640, 480, numero) for numero in range(2)]

    def abrir_webcam(_: int) -> CapturaFalsa:
        return CapturaFalsa(cuadros)

    cerrada = VentanaFalsa(1)
    correr_webcam(RecortadorYuNet(DetectorFalso()), servidor.cliente(), Ritmo(), modo_camara=False,
                  abrir=abrir_webcam, crear_ventana=lambda: cerrada, salida=lambda _: None, puerta=puerta)
    cliente.recibir("accesia/entrada/puerta/set", b"ABRIR")
    abierta = VentanaFalsa(1)
    correr_webcam(RecortadorYuNet(DetectorFalso()), servidor.cliente(), Ritmo(), modo_camara=False,
                  abrir=abrir_webcam, crear_ventana=lambda: abierta, salida=lambda _: None, puerta=puerta)

    assert cerrada.ultima is not None and not _es_verde(cerrada.ultima[2, 2])
    assert abierta.ultima is not None and _es_verde(abierta.ultima[2, 2])
