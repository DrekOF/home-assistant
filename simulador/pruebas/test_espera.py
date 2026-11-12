"""
Nombre: test_espera.py
Descripción: Pruebas de RF-01 · C2 en el simulador: espera 1 s desde cada respuesta, y 3 s tras permitido, denegado o desconocido, con un reloj falso.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path

import httpx
import pytest
from dobles import DetectorFalso, RelojFalso, ServidorFalso, escribir_foto, imagen_sintetica, respuesta_200

from simulador.carpeta import correr_carpeta
from simulador.envio import Respuesta
from simulador.recortador import RecortadorYuNet
from simulador.recorte import Cara
from simulador.ritmo import Ritmo

pytestmark = pytest.mark.marca("RF-01 · C6 · espera")


@pytest.mark.parametrize(
    ("resultado", "espera"),
    [
        ("descartado", 1.0),
        ("muestra_aceptada", 1.0),
        ("muestra_rechazada", 1.0),
        ("permitido", 3.0),
        ("denegado", 3.0),
        ("desconocido", 3.0),
    ],
)
def test_espera_segun_el_resultado(resultado: str, espera: float, reloj: RelojFalso) -> None:
    ritmo = Ritmo(reloj)
    assert ritmo.puede_enviar()

    assert ritmo.registrar(Respuesta(200, {"resultado": resultado})) == espera
    reloj.dormir(espera - 0.25)  # fracciones exactas en binario: el reloj suma sin redondeos
    assert not ritmo.puede_enviar()
    assert ritmo.falta() == 0.25
    reloj.dormir(0.25)
    assert ritmo.puede_enviar()


@pytest.mark.parametrize(("resultado", "espera"), [("descartado", 1.0), ("permitido", 3.0)])
def test_la_espera_se_cuenta_desde_la_respuesta(
    tmp_path: Path, reloj: RelojFalso, resultado: str, espera: float
) -> None:
    """El servidor tarda 2 s: el siguiente envío sale 2 s + la espera después del anterior, no solo la espera."""
    enviados: list[float] = []
    llegadas: list[float] = []

    def servidor_lento(_: httpx.Request) -> httpx.Response:
        enviados.append(reloj.ahora)
        reloj.dormir(2.0)
        llegadas.append(reloj.ahora)
        return respuesta_200(resultado)

    servidor = ServidorFalso(*[servidor_lento] * 3)
    for numero in range(3):
        escribir_foto(tmp_path / f"foto-{numero}.jpg", imagen_sintetica(320, 240, numero))

    codigo = correr_carpeta(
        tmp_path, RecortadorYuNet(DetectorFalso([Cara(100, 60, 80, 100)])), servidor.cliente(), Ritmo(reloj),
        modo_camara=False, dormir=reloj.dormir, salida=lambda _: None,
    )

    assert codigo == 0
    assert len(enviados) == 3
    for anterior, siguiente in zip(range(2), range(1, 3), strict=True):
        assert enviados[siguiente] == llegadas[anterior] + espera
        assert enviados[siguiente] - enviados[anterior] == 2.0 + espera
