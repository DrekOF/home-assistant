"""
Nombre: test_envio.py
Descripción: Pruebas del contrato cámara → servidor en el simulador: cabeceras, cuerpo JPEG de 100 000 bytes o menos y reacción a cada respuesta y error (servidor falso con httpx.MockTransport).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import re
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path

import httpx
import pytest
from dobles import (
    TOKEN,
    CapturaFalsa,
    DetectorFalso,
    RelojFalso,
    ServidorFalso,
    VentanaFalsa,
    escribir_foto,
    imagen_sintetica,
    respuesta_200,
    respuesta_error,
    ruido,
)

from simulador import VERSION
from simulador.carpeta import correr_carpeta
from simulador.comandos import principal
from simulador.envio import TIEMPO_ESPERA_S
from simulador.imagen import decodificar_jpeg
from simulador.recortador import LIMITE_BYTES, RecortadorYuNet, SinEnvio
from simulador.recorte import Cara
from simulador.ritmo import Ritmo, leer_retry_after
from simulador.webcam import correr_webcam

cabeceras = pytest.mark.marca("contrato cámara · cabeceras")
respuestas = pytest.mark.marca("contrato cámara · respuestas")


# --- Cabeceras y cuerpo ---


@cabeceras
def test_peticion_con_las_cuatro_cabeceras_y_un_jpeg(tmp_path: Path, servidor: ServidorFalso) -> None:
    escribir_foto(tmp_path / "foto.jpg", imagen_sintetica(640, 480))
    cara = Cara(250, 150, 110, 140, 0.9372)
    lineas: list[str] = []

    codigo = correr_carpeta(
        tmp_path, RecortadorYuNet(DetectorFalso([cara])), servidor.cliente("entrada"), Ritmo(),
        modo_camara=False, dormir=lambda _: None, salida=lineas.append,
    )

    assert codigo == 0
    [peticion] = servidor.peticiones
    assert peticion.method == "POST"
    assert peticion.url.path == "/api/v1/dispositivos/entrada/rostros"
    assert peticion.headers["Authorization"] == f"Bearer {TOKEN}"
    assert peticion.headers["Content-Type"] == "image/jpeg"
    assert peticion.headers["X-AccesIA-Firmware"] == f"simulador-{VERSION}"
    assert re.fullmatch(r"simulador-\d+\.\d+\.\d+", peticion.headers["X-AccesIA-Firmware"])
    assert peticion.headers["X-AccesIA-Puntaje"] == "0.937"
    assert 0 <= float(peticion.headers["X-AccesIA-Puntaje"]) <= 1

    cuerpo = peticion.content
    assert cuerpo[:2] == b"\xff\xd8" and cuerpo[-2:] == b"\xff\xd9"  # inicio y fin de un JPEG
    assert len(cuerpo) <= LIMITE_BYTES == 100_000
    # El recorte de la fórmula: (222, 115) a (388, 325).
    assert decodificar_jpeg(cuerpo).shape[:2] == (210, 166)
    # El token va solo en la cabecera, nunca en la salida.
    assert all(TOKEN not in linea for linea in lineas)


@cabeceras
def test_recorte_de_mas_de_100000_bytes_no_se_envia(tmp_path: Path, servidor: ServidorFalso) -> None:
    escribir_foto(tmp_path / "ruido.png", ruido(600, 600))
    recortador = RecortadorYuNet(DetectorFalso([Cara(100, 100, 400, 400)]))
    assert isinstance(resultado := recortador.procesar(ruido(600, 600)), SinEnvio)
    assert resultado.motivo == "recorte_grande"
    lineas: list[str] = []

    codigo = correr_carpeta(
        tmp_path, recortador, servidor.cliente(), Ritmo(), modo_camara=False, dormir=lambda _: None,
        salida=lineas.append,
    )

    assert codigo == 0
    assert servidor.peticiones == []
    assert any(re.search(r"ruido\.png: no se envía, el recorte pesa \d+ bytes", linea) for linea in lineas)


@cabeceras
def test_el_token_sale_de_token_camara(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.delenv("TOKEN_CAMARA", raising=False)
    assert principal(["carpeta", "datos/prueba", "--codigo", "entrada"]) == 2
    assert "TOKEN_CAMARA" in capsys.readouterr().err

    monkeypatch.setenv("TOKEN_CAMARA", TOKEN)
    assert principal(["carpeta", "carpeta-que-no-existe", "--codigo", "entrada"]) == 2
    salida = capsys.readouterr()
    assert TOKEN not in salida.out + salida.err


# --- Reacción a cada respuesta ---


def _registrar(servidor: ServidorFalso, ritmo: Ritmo, veces: int = 1) -> list[float]:
    cliente = servidor.cliente()
    return [ritmo.registrar(cliente.enviar(b"\xff\xd8jpeg\xff\xd9", 0.95)) for _ in range(veces)]


@respuestas
@pytest.mark.parametrize(("estado", "codigo"), [(401, "token_invalido"), (403, "dispositivo_inactivo")])
def test_401_y_403_esperan_30_s(estado: int, codigo: str, reloj: RelojFalso) -> None:
    ritmo = Ritmo(reloj)
    servidor = ServidorFalso(respuesta_error(estado, codigo), respuesta_error(estado, codigo))
    assert _registrar(servidor, ritmo, 2) == [30.0, 30.0]
    assert ritmo.falta() == 30.0


@respuestas
@pytest.mark.parametrize(("valor", "espera"), [("1", 1.0), ("7", 7.0), (None, 1.0), ("no-es-un-numero", 1.0)])
def test_429_espera_lo_que_diga_retry_after(valor: str | None, espera: float, reloj: RelojFalso) -> None:
    cabeceras_429 = {"Retry-After": valor} if valor is not None else None
    servidor = ServidorFalso(respuesta_error(429, "demasiadas_peticiones", cabeceras_429))
    assert _registrar(servidor, Ritmo(reloj)) == [espera]


@respuestas
def test_retry_after_tambien_puede_ser_una_fecha() -> None:
    ahora = datetime(2026, 11, 20, 12, 58, 12, tzinfo=UTC)
    assert leer_retry_after(format_datetime(ahora + timedelta(seconds=5), usegmt=True), ahora) == 5.0
    assert leer_retry_after(format_datetime(ahora - timedelta(seconds=5), usegmt=True), ahora) == 1.0


@respuestas
@pytest.mark.parametrize(
    "falla",
    [
        lambda: respuesta_error(503, "no_disponible"),
        lambda: httpx.ReadTimeout("sin respuesta"),
        lambda: httpx.ConnectError("conexión rechazada"),
    ],
    ids=["5xx", "sin respuesta en 5 s", "sin conexión"],
)
def test_fallas_esperan_1_2_4_y_hasta_10_s(falla, reloj: RelojFalso) -> None:
    # Seis fallas seguidas, una respuesta que reinicia la cuenta y otra falla.
    servidor = ServidorFalso(*[falla() for _ in range(6)], respuesta_200("descartado"), falla())
    assert _registrar(servidor, Ritmo(reloj), 8) == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0, 1.0, 1.0]


@respuestas
def test_fallas_mezcladas_siguen_la_misma_cuenta(reloj: RelojFalso) -> None:
    servidor = ServidorFalso(respuesta_error(500, "error"), httpx.ReadTimeout("lento"), respuesta_error(502, "x"))
    assert _registrar(servidor, Ritmo(reloj), 3) == [1.0, 2.0, 4.0]


@respuestas
@pytest.mark.parametrize(
    ("estado", "codigo"), [(413, "imagen_grande"), (415, "tipo_no_soportado"), (422, "imagen_invalida")]
)
def test_otros_errores_esperan_1_s(estado: int, codigo: str, reloj: RelojFalso) -> None:
    servidor = ServidorFalso(respuesta_error(estado, codigo))
    assert _registrar(servidor, Ritmo(reloj)) == [1.0]


@respuestas
def test_webcam_un_error_raro_cuenta_como_falla_y_espera(servidor: ServidorFalso) -> None:
    """Si el envío revienta por algo inesperado, la webcam no reintenta en cada cuadro: espera como ante una falla."""
    servidor.respuestas = [RuntimeError("algo inesperado")]
    lineas: list[str] = []
    codigo = correr_webcam(
        RecortadorYuNet(DetectorFalso([Cara(100, 60, 90, 110)])), servidor.cliente(), Ritmo(), modo_camara=False,
        abrir=lambda _: CapturaFalsa([imagen_sintetica(640, 480)] * 5), crear_ventana=lambda: VentanaFalsa(5),
        salida=lineas.append,
    )
    assert codigo == 0
    assert len(servidor.peticiones) == 1
    assert any("error al enviar (RuntimeError) (espera 1 s)" in linea for linea in lineas)


@respuestas
def test_sin_respuesta_en_5_s(servidor: ServidorFalso) -> None:
    assert TIEMPO_ESPERA_S == 5.0
    cliente = servidor.cliente()
    assert cliente._http.timeout == httpx.Timeout(5.0)
    servidor.respuestas = [httpx.ReadTimeout("sin respuesta")]
    respuesta = cliente.enviar(b"\xff\xd8jpeg\xff\xd9", None)
    assert respuesta.estado is None
    assert respuesta.falla == "sin respuesta en 5 s"
    assert "X-AccesIA-Puntaje" not in servidor.peticiones[0].headers
