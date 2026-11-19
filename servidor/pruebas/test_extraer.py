"""
Nombre: test_extraer.py
Descripción: Pruebas «RF-10 · C4», «contrato cámara · modo extraer» y «RNF-01 · C1» del modo extraer: una cámara de respaldo falsa, sin red, que entrega cuadros completos por HTTP, con la visión armada, el reloj de las pruebas, la conexión de la prueba y el broker de prueba.
Fecha de creación: 2026-11-18
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.0
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import armar
import cv2
import httpx
import numpy as np
import pytest
from sqlalchemy import Connection, text
from vision_falsa import CaraArmada, eje

from accesia import extraer as modulo
from accesia.extraer import ModoExtraer, Paso
from accesia.mqtt import Publicacion

URL = "http://192.168.137.60/capture"
OTRA_URL = "http://192.168.137.61/capture"
ANA = "Ana María Gómez"
EVENTO = "accesia/patio/evento"

# Un cuadro completo gris de 640 × 480: la visión armada no mira sus píxeles.
_ok, _jpeg = cv2.imencode(".jpg", np.full((480, 640, 3), 128, dtype=np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 80])
CUADRO = _jpeg.tobytes()


class CamaraHttp:
    """La cámara de respaldo vista desde el servidor: responde cada GET como la prueba le diga, sin red."""

    def __init__(self) -> None:
        self.pedidos: list[str] = []
        self.respuestas: list[Callable] = []  # una por pedido; cuando se acaban, entrega el cuadro

    def responder(self, *respuestas: Callable) -> None:
        self.respuestas = list(respuestas)

    async def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(str(pedido.url))
        respuesta = self.respuestas.pop(0) if self.respuestas else foto
        resultado = respuesta(pedido)
        return await resultado if asyncio.iscoroutine(resultado) else resultado


def foto(_pedido: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=CUADRO, headers={"Content-Type": "image/jpeg"})


def sin_red(pedido: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("sin red", request=pedido)


def contacto(conexion: Connection, codigo: str = "patio"):
    return conexion.execute(
        text("SELECT ultimo_contacto FROM dispositivo WHERE codigo = :codigo"), {"codigo": codigo}
    ).scalar_one()


@pytest.fixture
def camara_http() -> CamaraHttp:
    return CamaraHttp()


@pytest.fixture
def patio(conexion: Connection) -> str:
    return armar.camara(conexion, "patio", "respaldo", url_captura=URL)


class Prueba:
    """El modo extraer de la app de la prueba, con la cámara falsa y una espera que solo anota los segundos."""

    def __init__(self, estado, conexiones, camara: Callable, **opciones) -> None:
        self.esperas: list[float] = []
        self.antes_de_esperar: Callable[[int], object] | None = None
        self.modo = ModoExtraer(
            estado, conexiones=conexiones, transporte=httpx.MockTransport(camara), dormir=self._dormir, **opciones
        )

    async def _dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)
        if self.antes_de_esperar is not None:
            self.antes_de_esperar(len(self.esperas))
        await asyncio.sleep(0.01)

    def capturar(self, codigo: str = "patio") -> Paso:
        return asyncio.run(self.modo.una_captura(codigo))


@pytest.fixture
def extraer(app, vision, conexion_por_turnos, camara_http) -> Prueba:
    return Prueba(app.state, conexion_por_turnos, camara_http, tiempo_de_espera_s=0.2)


def marcar(servidor, escucha) -> None:
    """Si llega la marca, ya llegó todo lo que el servidor publicó antes por esa conexión."""
    carga = uuid.uuid4().hex
    assert servidor.publicar(Publicacion("accesia/prueba/marca", carga, 1, False))
    escucha.esperar("accesia/prueba/marca", lambda mensaje: mensaje.carga == carga)


# --- RF-10 · C4: una cámara de respaldo reconoce e inscribe como cualquier otra ---


@pytest.mark.marca("RF-10 · C4")
def test_un_permitido_por_el_modo_extraer_guarda_su_evento_y_el_contacto(
    extraer, patio, vision, conexion: Connection, reloj
) -> None:
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))
    vision.preparar([CaraArmada(huella=eje(0))])

    paso = extraer.capturar()

    assert (paso.sigue, paso.resultado, paso.falla) == (True, "permitido", None)
    (evento,) = armar.eventos(conexion)
    assert (evento.dispositivo_codigo, evento.persona_id, evento.resultado) == ("patio", ana, "permitido")
    assert contacto(conexion) == reloj.momento


@pytest.mark.marca("RF-10 · C4")
def test_un_desconocido_por_el_modo_extraer_guarda_su_evento(extraer, patio, vision, conexion: Connection) -> None:
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    vision.preparar([CaraArmada(huella=eje(7))])

    paso = extraer.capturar()

    assert paso.resultado == "desconocido"
    (evento,) = armar.eventos(conexion)
    assert (evento.dispositivo_codigo, evento.persona_id, evento.resultado) == ("patio", None, "desconocido")


@pytest.mark.marca("RF-10 · C4")
def test_una_camara_de_respaldo_inscribe_por_el_mismo_camino(
    extraer, patio, vision, conexion: Connection, reloj
) -> None:
    persona = armar.persona(conexion)
    armar.consentimiento(conexion, persona, aceptado_en=datetime.now(UTC) - timedelta(hours=1))
    inscripcion = armar.inscripcion(conexion, persona, "patio", vence=reloj.momento + timedelta(seconds=120))
    vision.preparar([CaraArmada(huella=eje(3))])

    paso = extraer.capturar()

    assert (paso.resultado, paso.espera) == ("muestra_aceptada", 1)
    muestra = conexion.execute(
        text("SELECT fuente, inscripcion_id FROM rostro WHERE persona_id = :persona"), {"persona": persona}
    ).one()
    assert (muestra.fuente, muestra.inscripcion_id) == ("respaldo", inscripcion)
    assert armar.eventos(conexion) == []


@pytest.mark.marca("RF-10 · C4")
def test_un_cuadro_sin_cara_no_guarda_evento_ni_escribe_en_el_registro(
    extraer, patio, vision, conexion: Connection, reloj, caplog
) -> None:
    caplog.set_level(logging.INFO, logger="accesia")
    vision.preparar([])

    paso = extraer.capturar()

    assert (paso.sigue, paso.resultado, paso.falla, paso.espera) == (True, None, None, 1)
    assert armar.eventos(conexion) == []
    assert vision.imagenes == 1, "Sin cara en el cuadro no hay recorte que procesar."
    assert [r.getMessage() for r in caplog.records if r.name.startswith("accesia")] == []
    assert contacto(conexion) == reloj.momento, "Una captura buena cuenta como contacto aunque no tenga cara."


@pytest.mark.marca("RF-10 · C4")
def test_una_cara_mas_pequena_que_cara_min_px_no_se_procesa(extraer, patio, vision, conexion: Connection) -> None:
    # Como la cámara del contrato: no envía caras de menos de CARA_MIN_PX (80 px por defecto).
    vision.preparar([CaraArmada(alto=60)])

    paso = extraer.capturar()

    assert paso.resultado is None
    assert vision.imagenes == 1
    assert armar.eventos(conexion) == []


@pytest.mark.marca("RF-10 · C4")
@pytest.mark.parametrize(
    ("respuesta", "motivo"),
    [
        (lambda pedido: httpx.Response(500), "respondió 500"),
        (lambda pedido: httpx.Response(404), "respondió 404"),
        (lambda pedido: httpx.Response(302, headers={"Location": OTRA_URL}), "redirige"),
        (lambda pedido: httpx.Response(200, content=b"<html>no soy una foto</html>"), "no devolvió un JPEG"),
        (sin_red, "no se pudo alcanzar"),
    ],
    ids=["500", "404", "redirección", "no es JPEG", "sin conexión"],
)
def test_una_falla_de_la_url_no_guarda_nada_y_el_bucle_sigue(
    extraer, patio, camara_http, vision, conexion: Connection, respuesta, motivo
) -> None:
    vision.preparar([CaraArmada(huella=eje(0))])
    camara_http.responder(respuesta)

    paso = extraer.capturar()

    assert paso.sigue and paso.resultado is None
    assert motivo in paso.falla
    assert armar.eventos(conexion) == []
    assert contacto(conexion) is None, "Una captura fallida no cuenta como contacto."
    assert camara_http.pedidos == [URL], "No se siguen redirecciones."


@pytest.mark.marca("RF-10 · C4")
def test_una_url_que_no_responde_a_tiempo_es_una_falla(extraer, patio, camara_http, conexion: Connection) -> None:
    async def lenta(pedido):
        await asyncio.sleep(2)
        return foto(pedido)

    camara_http.responder(lenta)
    inicio = time.perf_counter()

    paso = extraer.capturar()

    assert time.perf_counter() - inicio < 1.5, "El tiempo de espera es del pedido completo."
    assert "no respondió en" in paso.falla
    assert contacto(conexion) is None


@pytest.mark.marca("RF-10 · C4")
@pytest.mark.parametrize("con_largo", [True, False], ids=["con Content-Length", "sin Content-Length"])
def test_un_cuadro_mas_grande_que_el_tope_se_corta(app, vision, conexion_por_turnos, camara_http, patio, con_largo):
    async def trozos():
        for inicio in range(0, len(CUADRO), 500):
            yield CUADRO[inicio : inicio + 500]

    camara_http.responder(lambda pedido: httpx.Response(200, content=CUADRO if con_largo else trozos()))
    prueba = Prueba(app.state, conexion_por_turnos, camara_http, tiempo_de_espera_s=0.2, tope_bytes=1000)

    paso = prueba.capturar()

    assert "más de" in paso.falla


@pytest.mark.marca("RF-10 · C4")
def test_una_url_que_no_es_http_no_se_pide(app, vision, conexion: Connection, conexion_por_turnos, camara_http):
    armar.camara(conexion, "patio", "respaldo", url_captura="ftp://192.168.137.60/foto.jpg")
    prueba = Prueba(app.state, conexion_por_turnos, camara_http, tiempo_de_espera_s=0.2)

    paso = prueba.capturar()

    assert "no es http ni https" in paso.falla
    assert camara_http.pedidos == []


@pytest.mark.marca("RF-10 · C4")
def test_las_fallas_esperan_cada_vez_mas_y_el_registro_las_dice_una_vez(
    extraer, patio, camara_http, vision, caplog
) -> None:
    caplog.set_level(logging.INFO, logger="accesia")
    vision.preparar([])
    camara_http.responder(*[lambda pedido: httpx.Response(500)] * 6)

    esperas = [extraer.capturar().espera for _ in range(7)]

    assert esperas == [1, 2, 4, 8, 10, 10, 1], "Como la cámara con un 5xx: 1, 2, 4 y hasta 10 s; al volver, 1 s."
    lineas = [r for r in caplog.records if r.name == "accesia.extraer"]
    assert [r.levelno for r in lineas] == [logging.WARNING, logging.INFO]
    assert "respondió 500" in lineas[0].getMessage()
    assert "vuelve a capturar" in lineas[1].getMessage()


@pytest.mark.marca("RF-10 · C4")
def test_si_cambia_el_motivo_de_la_falla_lo_dice_otra_vez(extraer, patio, camara_http, caplog) -> None:
    caplog.set_level(logging.INFO, logger="accesia")
    camara_http.responder(lambda p: httpx.Response(500), lambda p: httpx.Response(500), lambda p: httpx.Response(404))

    for _ in range(3):
        extraer.capturar()

    avisos = [r.getMessage() for r in caplog.records if r.name == "accesia.extraer"]
    assert len(avisos) == 2 and "500" in avisos[0] and "404" in avisos[1]


@pytest.mark.marca("RF-10 · C4")
def test_el_registro_no_muestra_el_usuario_ni_la_clave_de_la_url(
    app, vision, conexion: Connection, conexion_por_turnos, camara_http, caplog
) -> None:
    caplog.set_level(logging.INFO, logger="accesia")
    armar.camara(conexion, "patio", "respaldo", url_captura="http://admin:clave-secreta@192.168.137.60/capture?t=xyz")
    camara_http.responder(lambda pedido: httpx.Response(500))
    prueba = Prueba(app.state, conexion_por_turnos, camara_http, tiempo_de_espera_s=0.2)

    prueba.modo.avisar_inicio("patio", "http://admin:clave-secreta@192.168.137.60/capture?t=xyz")
    prueba.capturar()

    texto = " ".join(r.getMessage() for r in caplog.records)
    assert "clave-secreta" not in texto and "admin" not in texto and "xyz" not in texto
    assert "http://192.168.137.60/capture" in texto


@pytest.mark.marca("RF-10 · C4")
@pytest.mark.parametrize(
    "cambio",
    [
        "UPDATE dispositivo SET activo = false WHERE codigo = 'patio'",
        "DELETE FROM dispositivo WHERE codigo = 'patio'",
        "UPDATE dispositivo SET tipo = 'simulador' WHERE codigo = 'patio'",
    ],
    ids=["desactivada", "borrada", "otro tipo"],
)
def test_una_camara_desactivada_borrada_o_de_otro_tipo_deja_de_pedirse(
    extraer, patio, camara_http, vision, conexion: Connection, cambio
) -> None:
    vision.preparar([])
    assert extraer.capturar().sigue
    conexion.execute(text(cambio))

    paso = extraer.capturar()

    assert not paso.sigue
    assert camara_http.pedidos == [URL], "Después del cambio no pide más cuadros."


@pytest.mark.marca("RF-10 · C4")
def test_si_cambia_la_url_pide_la_nueva(extraer, patio, camara_http, vision, conexion: Connection) -> None:
    vision.preparar([])
    extraer.capturar()
    conexion.execute(text("UPDATE dispositivo SET url_captura = :url WHERE codigo = 'patio'"), {"url": OTRA_URL})

    extraer.capturar()

    assert camara_http.pedidos == [URL, OTRA_URL]


@pytest.mark.marca("RF-10 · C4")
@pytest.mark.parametrize(
    ("cambio", "sigue"),
    [
        ("UPDATE dispositivo SET activo = false WHERE codigo = 'patio'", False),
        (f"UPDATE dispositivo SET url_captura = '{OTRA_URL}' WHERE codigo = 'patio'", True),
    ],
    ids=["la desactivan", "le cambian la URL"],
)
def test_si_la_camara_cambia_mientras_se_pide_el_cuadro_no_cuenta(
    extraer, patio, camara_http, vision, conexion: Connection, conexion_por_turnos, cambio, sigue
) -> None:
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    vision.preparar([CaraArmada(huella=eje(0))])

    def cambia_y_entrega(pedido: httpx.Request) -> httpx.Response:
        with conexion_por_turnos() as abierta:  # como una petición de la web, mientras la cámara responde
            abierta.execute(text(cambio))
        return foto(pedido)

    camara_http.responder(cambia_y_entrega)

    paso = extraer.capturar()

    assert (paso.sigue, paso.resultado) == (sigue, None)
    assert armar.eventos(conexion) == [], "Ese cuadro era de la cámara de antes del cambio."
    assert contacto(conexion) is None


@pytest.mark.marca("RF-10 · C4")
def test_vigilar_sigue_despues_de_las_fallas_y_para_al_desactivar(
    extraer, patio, camara_http, vision, conexion_por_turnos
) -> None:
    vision.preparar([])
    camara_http.responder(lambda p: httpx.Response(500), lambda p: httpx.Response(500))

    def al_esperar(veces: int) -> None:
        if veces == 4:  # como una petición de la web que desactiva la cámara
            with conexion_por_turnos() as abierta:
                abierta.execute(text("UPDATE dispositivo SET activo = false WHERE codigo = 'patio'"))

    extraer.antes_de_esperar = al_esperar

    asyncio.run(asyncio.wait_for(extraer.modo.vigilar("patio"), timeout=10))

    assert extraer.esperas == [1, 2, 1, 1]
    assert len(camara_http.pedidos) == 4


@pytest.mark.marca("RF-10 · C4")
def test_un_error_inesperado_no_tumba_el_bucle(extraer, patio, vision, monkeypatch, caplog) -> None:
    caplog.set_level(logging.INFO, logger="accesia")
    vision.preparar([])
    llamadas = []

    def falla_una_vez(*argumentos):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError("falla de prueba")
        return original(*argumentos)

    original = modulo.extraer_recorte
    monkeypatch.setattr(modulo, "extraer_recorte", falla_una_vez)

    primero, segundo = extraer.capturar(), extraer.capturar()

    assert primero.sigue and "RuntimeError" in primero.falla
    assert segundo.sigue and segundo.falla is None
    assert any(r.exc_info for r in caplog.records if r.name == "accesia.extraer"), "El error queda con su traza."


@pytest.mark.marca("RF-10 · C4")
def test_el_supervisor_pide_cada_camara_en_paralelo_y_encuentra_las_nuevas(
    app, vision, conexion: Connection, conexion_por_turnos
) -> None:
    pedidos: list[str] = []

    async def rutas(pedido: httpx.Request) -> httpx.Response:
        if pedido.url.host == "192.168.137.70":
            await asyncio.sleep(5)  # nunca responde a tiempo
        pedidos.append(str(pedido.url))
        return foto(pedido)

    armar.camara(conexion, "lenta", "respaldo", url_captura="http://192.168.137.70/capture")
    armar.camara(conexion, "patio", "respaldo", url_captura=URL)
    vision.preparar([])
    prueba = Prueba(app.state, conexion_por_turnos, rutas, tiempo_de_espera_s=0.3, revisar_cada_s=0.05)

    async def correr() -> None:
        tarea = asyncio.create_task(prueba.modo.correr())
        try:
            # La lenta tarda 0,3 s en fallar cada vez; mientras tanto, la de patio sigue pidiendo.
            await esperar_hasta(lambda: pedidos.count(URL) >= 5, 5)
            with conexion_por_turnos() as abierta:  # como una petición de la web que crea una cámara
                armar.camara(abierta, "nueva", "respaldo", url_captura=OTRA_URL)
            await esperar_hasta(lambda: OTRA_URL in pedidos, 5)
        finally:
            tarea.cancel()
            await asyncio.gather(tarea, return_exceptions=True)

    asyncio.run(correr())

    assert OTRA_URL in pedidos, "Una cámara nueva empieza sin reiniciar."
    assert "http://192.168.137.70/capture" not in pedidos, "La lenta nunca respondió a tiempo."


async def esperar_hasta(condicion: Callable[[], bool], segundos: float) -> None:
    limite = time.monotonic() + segundos
    while not condicion():
        assert time.monotonic() < limite, "No se cumplió a tiempo."
        await asyncio.sleep(0.01)


@pytest.mark.marca("RF-10 · C4")
def test_el_evento_del_modo_extraer_se_publica_en_mqtt(
    extraer, patio, vision, conexion: Connection, mqtt_servidor, escucha
) -> None:
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))
    vision.preparar([CaraArmada(huella=eje(0))])

    extraer.capturar()

    evento = escucha.esperar(EVENTO).json()
    assert (evento["dispositivo"], evento["resultado"], evento["persona"]["id"]) == ("patio", "permitido", str(ana))


@pytest.mark.marca("RF-10 · C4")
def test_si_la_transaccion_no_se_confirma_no_se_publica_nada(
    app, vision, patio, conexion: Connection, conexion_por_turnos, camara_http, mqtt_servidor, escucha
) -> None:
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    vision.preparar([CaraArmada(huella=eje(0))])
    usos = []

    @contextmanager
    def falla_al_confirmar():
        usos.append(1)
        with conexion_por_turnos() as abierta:
            yield abierta
            if len(usos) == 2:  # la transacción del recorte, después de guardar el evento
                raise RuntimeError("la base no confirmó")

    prueba = Prueba(app.state, falla_al_confirmar, camara_http, tiempo_de_espera_s=0.2)

    paso = prueba.capturar()

    assert paso.falla is not None
    marcar(mqtt_servidor, escucha)
    assert escucha.mensajes(EVENTO) == []
    assert armar.eventos(conexion) == []


# --- contrato cámara · modo extraer ---


@pytest.mark.marca("contrato cámara · modo extraer")
def test_cada_segundo_con_3_s_de_espera_como_dice_el_contrato() -> None:
    assert modulo.ESPERA_S == 1
    assert modulo.TIEMPO_DE_ESPERA_S == 3
    assert modulo.ESPERA_TRAS_EVENTO_S == 3
    assert ModoExtraer.__init__.__kwdefaults__["tiempo_de_espera_s"] == modulo.TIEMPO_DE_ESPERA_S


@pytest.mark.marca("contrato cámara · modo extraer")
def test_el_recorte_sale_del_cuadro_con_la_formula_del_contrato(extraer, patio, vision) -> None:
    # Caja de YuNet en (100, 80) de 96 × 120: con 25 % de margen, de (76, 50) a (220, 230).
    vision.preparar([CaraArmada(x=100, y=80, alto=120)])

    extraer.capturar()

    assert vision.formas == [(480, 640), (180, 144)], "Primero el cuadro completo y después el recorte."


@pytest.mark.marca("contrato cámara · modo extraer")
@pytest.mark.parametrize(
    ("armar_persona", "huella", "resultado", "espera"),
    [
        (lambda c: armar.inscrita(c, ANA, "1075000001", eje(0)), eje(0), "permitido", 3),
        (lambda c: armar.inscrita(c, ANA, "1075000001", eje(0), activa=False), eje(0), "denegado", 3),
        (lambda c: armar.inscrita(c, ANA, "1075000001", eje(0)), eje(9), "desconocido", 3),
    ],
    ids=["permitido", "denegado", "desconocido"],
)
def test_despues_de_un_evento_espera_3_s_como_la_camara(
    extraer, patio, vision, conexion: Connection, armar_persona, huella, resultado, espera
) -> None:
    armar_persona(conexion)
    vision.preparar([CaraArmada(huella=huella)])

    paso = extraer.capturar()

    assert (paso.resultado, paso.espera) == (resultado, espera)


@pytest.mark.marca("contrato cámara · modo extraer")
def test_el_recorte_va_por_el_camino_de_enviar_rostro(extraer, patio, vision, monkeypatch) -> None:
    from accesia import rostros

    vistos = []
    original = rostros.procesar

    def espia(conexion, camara, datos, vision_, momento, inicio, firmware=None, alertas=None):
        vistos.append((camara.codigo, camara.tipo, datos[:2], firmware))
        return original(conexion, camara, datos, vision_, momento, inicio, firmware, alertas)

    monkeypatch.setattr(rostros, "procesar", espia)
    vision.preparar([CaraArmada(huella=eje(0))])

    extraer.capturar()

    assert vistos == [("patio", "respaldo", b"\xff\xd8", "modo-extraer")], "Un JPEG, con su firmware en el registro."


# --- RNF-01 · C1: nada en disco ni en el registro ---


@pytest.mark.marca("RNF-01 · C1")
def test_el_modo_extraer_no_escribe_cuadros_en_disco_ni_en_el_registro(
    extraer, patio, vision, conexion: Connection, monkeypatch, caplog
) -> None:
    caplog.set_level(logging.DEBUG)

    def prohibido(*_argumentos, **_opciones):
        raise AssertionError("Se intentó escribir una imagen en disco.")

    monkeypatch.setattr(cv2, "imwrite", prohibido)
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    vision.preparar([CaraArmada(huella=eje(0))])

    assert extraer.capturar().resultado == "permitido"

    texto = " ".join(r.getMessage() for r in caplog.records)
    assert "/9j/" not in texto and "\\xff\\xd8" not in texto, "Ni el cuadro ni el recorte van al registro."
