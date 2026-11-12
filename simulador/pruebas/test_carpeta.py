"""
Nombre: test_carpeta.py
Descripción: Pruebas del modo carpeta (api-dispositivo.md · Pruebas de contrato): orden por nombre, comparación con esperado.json, resumen y código de salida.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import json
from pathlib import Path

import pytest
from dobles import DetectorFalso, ServidorFalso, escribir_foto, imagen_sintetica, respuesta_200, respuesta_error

from simulador.carpeta import correr_carpeta
from simulador.recortador import RecortadorYuNet
from simulador.recorte import Cara
from simulador.ritmo import Ritmo
from simulador.rutas import RAIZ, resolver_carpeta

pytestmark = pytest.mark.marca("contrato cámara · modo carpeta")

CARA = Cara(100, 60, 90, 110, 0.95)


def _carpeta(tmp_path: Path, nombres: list[str], esperado: dict | str | None = None) -> Path:
    for numero, nombre in enumerate(nombres):
        escribir_foto(tmp_path / nombre, imagen_sintetica(320, 240, numero))
    if esperado is not None:
        texto = esperado if isinstance(esperado, str) else json.dumps(esperado, ensure_ascii=False)
        (tmp_path / "esperado.json").write_text(texto, encoding="utf-8")
    return tmp_path


def _correr(carpeta: Path, servidor: ServidorFalso, detector: DetectorFalso | None = None) -> tuple[int, list[str]]:
    lineas: list[str] = []
    codigo = correr_carpeta(
        carpeta, RecortadorYuNet(detector or DetectorFalso([CARA])), servidor.cliente(), Ritmo(),
        modo_camara=False, dormir=lambda _: None, salida=lineas.append,
    )
    return codigo, lineas


ESPERADO = {
    "fotos": {
        "ana-01.jpg": {"resultado": "permitido", "persona": "Ana Gómez"},
        "ana-02.jpg": {"resultado": "permitido", "repetido": True},
        "bruno-01.jpg": {"resultado": "desconocido", "motivo": "bajo_umbral", "persona": None},
        "pared.jpg": {"enviada": False},
    }
}
NOMBRES = ["ana-01.jpg", "ana-02.jpg", "bruno-01.jpg", "pared.jpg"]


def _respuestas_bien() -> list:
    return [
        respuesta_200("permitido", persona="Ana Gómez", similitud=0.71),
        respuesta_200("permitido", persona="Ana Gómez", similitud=0.69, repetido=True),
        respuesta_200("desconocido", motivo="bajo_umbral", similitud=0.21),
    ]


def _detector_sin_cara_en_la_pared() -> DetectorFalso:
    return DetectorFalso(por_llamada=[[CARA], [CARA], [CARA], []])


def test_todo_coincide_y_termina_con_0(tmp_path: Path) -> None:
    servidor = ServidorFalso(*_respuestas_bien())
    codigo, lineas = _correr(_carpeta(tmp_path, NOMBRES, ESPERADO), servidor, _detector_sin_cara_en_la_pared())

    assert codigo == 0
    assert len(servidor.peticiones) == 3
    assert "Resumen: 4 fotos, 4 con respuesta esperada, 0 con diferencias." in lineas
    assert any("ana-01.jpg: permitido · motivo: — · persona: Ana Gómez · similitud: 0,710" in linea
               for linea in lineas)


def test_una_diferencia_termina_con_1_y_la_muestra(tmp_path: Path) -> None:
    respuestas = _respuestas_bien()
    respuestas[2] = respuesta_200("permitido", persona="Bruno Díaz", similitud=0.5)
    servidor = ServidorFalso(*respuestas)
    codigo, lineas = _correr(_carpeta(tmp_path, NOMBRES, ESPERADO), servidor, _detector_sin_cara_en_la_pared())

    assert codigo == 1
    assert "Resumen: 4 fotos, 4 con respuesta esperada, 1 con diferencias." in lineas
    assert '  bruno-01.jpg: resultado: se esperaba "desconocido" y llegó "permitido"' in lineas
    assert '  bruno-01.jpg: motivo: se esperaba "bajo_umbral" y llegó null' in lineas
    assert '  bruno-01.jpg: persona: se esperaba null y llegó "Bruno Díaz"' in lineas


def test_enviada_false_falla_si_se_envia(tmp_path: Path) -> None:
    servidor = ServidorFalso(*_respuestas_bien(), respuesta_200("descartado", motivo="sin_cara"))
    codigo, lineas = _correr(_carpeta(tmp_path, NOMBRES, ESPERADO), servidor)  # encuentra cara también en la pared

    assert codigo == 1
    assert "  pared.jpg: se envió y se esperaba que no" in lineas


def test_respuesta_esperada_de_una_foto_que_no_se_envio(tmp_path: Path) -> None:
    esperado = {"fotos": {"ana-01.jpg": {"resultado": "permitido"}}}
    codigo, lineas = _correr(_carpeta(tmp_path, ["ana-01.jpg"], esperado), ServidorFalso(), DetectorFalso([]))

    assert codigo == 1
    assert "  ana-01.jpg: no se envió (sin cara)" in lineas


def test_error_http_cuando_se_esperaba_un_resultado(tmp_path: Path) -> None:
    esperado = {"fotos": {"ana-01.jpg": {"resultado": "permitido"}}}
    servidor = ServidorFalso(respuesta_error(503, "no_disponible"))
    codigo, lineas = _correr(_carpeta(tmp_path, ["ana-01.jpg"], esperado), servidor)

    assert codigo == 1
    assert "  ana-01.jpg: se esperaba una respuesta 200 y llegó HTTP 503 no_disponible" in lineas


def test_foto_esperada_que_no_esta_en_la_carpeta(tmp_path: Path) -> None:
    esperado = {"fotos": {"ana-01.jpg": {"enviada": True}, "falta.jpg": {"resultado": "permitido"}}}
    codigo, lineas = _correr(_carpeta(tmp_path, ["ana-01.jpg"], esperado), ServidorFalso())

    assert codigo == 1
    assert "  falta.jpg: está en esperado.json pero no en la carpeta" in lineas


def test_sin_esperado_json_envia_todo_y_termina_con_0(tmp_path: Path) -> None:
    servidor = ServidorFalso()
    codigo, lineas = _correr(_carpeta(tmp_path, ["a.jpg", "b.jpg"]), servidor)

    assert codigo == 0
    assert len(servidor.peticiones) == 2
    assert lineas[-1] == "Listo: 2 fotos. La carpeta no trae esperado.json: no se comparó nada."


def test_envia_en_orden_por_nombre(tmp_path: Path) -> None:
    respuestas = [respuesta_200("descartado", motivo=nombre) for nombre in ("1", "2", "3", "4")]
    servidor = ServidorFalso(*respuestas)
    codigo, lineas = _correr(_carpeta(tmp_path, ["b-02.jpg", "C-01.png", "a-10.jpeg", "a-09.JPG"]), servidor)

    assert codigo == 0
    assert [linea.split(":")[0] for linea in lineas[:4]] == ["a-09.JPG", "a-10.jpeg", "b-02.jpg", "C-01.png"]


@pytest.mark.parametrize(
    "esperado",
    [
        "{ esto no es json",
        json.dumps({"ana-01.jpg": {"resultado": "permitido"}}),
        json.dumps({"fotos": {"ana-01.jpg": {"resulatdo": "permitido"}}}),
        json.dumps({"fotos": {"ana-01.jpg": {"enviada": "no"}}}),
        json.dumps({"fotos": {"ana-01.jpg": {"enviada": False, "resultado": "permitido"}}}),
    ],
    ids=["no es json", "sin fotos", "campo mal escrito", "enviada no booleana", "no enviada con respuesta"],
)
def test_esperado_mal_escrito_termina_con_2_sin_enviar(tmp_path: Path, esperado: str) -> None:
    servidor = ServidorFalso()
    codigo, lineas = _correr(_carpeta(tmp_path, ["ana-01.jpg"], esperado), servidor)

    assert codigo == 2
    assert servidor.peticiones == []
    assert "esperado.json" in lineas[0]


def test_esperado_con_bom_de_windows(tmp_path: Path) -> None:
    carpeta = _carpeta(tmp_path, ["ana-01.jpg"])
    (carpeta / "esperado.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"fotos": {}}).encode("utf-8"))
    codigo, _ = _correr(carpeta, ServidorFalso())
    assert codigo == 0


@pytest.mark.parametrize(("estado", "codigo_error"), [(401, "token_invalido"), (403, "dispositivo_inactivo")])
def test_token_rechazado_detiene_con_2(tmp_path: Path, estado: int, codigo_error: str) -> None:
    servidor = ServidorFalso(respuesta_error(estado, codigo_error))
    codigo, lineas = _correr(_carpeta(tmp_path, ["a.jpg", "b.jpg", "c.jpg"]), servidor)

    assert codigo == 2
    assert len(servidor.peticiones) == 1
    assert any(f"HTTP {estado} {codigo_error}" in linea for linea in lineas)
    assert "revisa $env:TOKEN_CAMARA" in lineas[-1]


def test_carpeta_sin_fotos_termina_con_2(tmp_path: Path) -> None:
    codigo, lineas = _correr(tmp_path, ServidorFalso())
    assert codigo == 2
    assert "no tiene fotos" in lineas[0]


def test_ruta_relativa_desde_la_raiz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`uv run simulador carpeta datos/prueba` funciona desde simulador/ como desde la raíz."""
    monkeypatch.chdir(tmp_path)
    assert resolver_carpeta(Path("specs/contratos")) == RAIZ / "specs" / "contratos"
    (tmp_path / "local").mkdir()
    assert resolver_carpeta(Path("local")) == Path("local")
    assert resolver_carpeta(Path("no-existe")) == Path("no-existe")
