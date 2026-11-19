"""
Nombre: test_mqtt.py
Descripción: Pruebas del servidor en MQTT con Mosquitto en un contenedor: disponibilidad, Evento (después de confirmar y solo con conexión), la parte de MQTT de R4, Resumen, la salud y la disponibilidad y el estado de las cámaras (contrato MQTT, R4, RF-10 · C3, RNF-01 · C3 y contrato API · salud).
Fecha de creación: 2026-11-12
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.1
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from mqtt_de_prueba import ClienteDePrueba, hasta, retenidos
from sqlalchemy import Connection
from vision_falsa import CaraArmada, eje, parecida

from accesia.asistencia import registrar_llegada
from accesia.mqtt import Publicacion, resumen_periodico

BOGOTA = ZoneInfo("America/Bogota")
ANA = "Ana María Gómez"
BRUNO = "Bruno Díaz"
DAVID = "David Peña"
ELENA = "Elena Ruiz"
EVENTO = "accesia/entrada/evento"
RESUMEN = "accesia/resumen"
DISPONIBLE = "accesia/servidor/disponible"


def hora(dia: int, horas: int, minutos: int, segundos: int = 0) -> datetime:
    return datetime(2026, 11, dia, horas, minutos, segundos, tzinfo=BOGOTA)


def marcar(servidor, escucha) -> None:
    """Publica una marca por la conexión del servidor y espera a que llegue. Un cliente entrega sus mensajes en
    orden: si llegó la marca, ya llegó todo lo que el servidor publicó antes."""
    carga = uuid.uuid4().hex
    assert servidor.publicar(Publicacion("accesia/prueba/marca", carga, 1, False))
    escucha.esperar("accesia/prueba/marca", lambda mensaje: mensaje.carga == carga)


def eventos(escucha, tema: str = EVENTO) -> list[dict]:
    return [mensaje.json() for mensaje in escucha.mensajes(tema)]


# --- contrato MQTT · disponible ---


@pytest.mark.marca("contrato MQTT · disponible")
def test_al_conectarse_publica_online_retenido_con_qos_1(mqtt_servidor, escucha, broker_mqtt) -> None:
    mensaje = escucha.esperar(DISPONIBLE, lambda m: m.carga == "online")

    assert mensaje.qos == 1
    assert retenidos(broker_mqtt, DISPONIBLE) == {DISPONIBLE: "online"}


@pytest.mark.marca("contrato MQTT · disponible")
def test_al_detenerse_deja_offline_retenido(conectar_mqtt, escucha, broker_mqtt) -> None:
    servidor = conectar_mqtt()

    servidor.detener()

    escucha.esperar(DISPONIBLE, lambda m: m.carga == "offline")
    assert retenidos(broker_mqtt, DISPONIBLE) == {DISPONIBLE: "offline"}


@pytest.mark.marca("contrato MQTT · disponible")
def test_si_la_conexion_se_corta_el_ultimo_deseo_publica_offline(conectar_mqtt, escucha, broker_mqtt) -> None:
    servidor = conectar_mqtt()

    # Sin el hilo de red nadie envía DISCONNECT: el broker solo ve la conexión cortada y publica el último deseo.
    servidor._cliente.loop_stop()
    servidor._cliente.socket().close()

    mensaje = escucha.esperar(DISPONIBLE, lambda m: m.carga == "offline")
    assert mensaje.qos == 1
    assert retenidos(broker_mqtt, DISPONIBLE) == {DISPONIBLE: "offline"}


# --- contrato MQTT · evento ---


@pytest.mark.marca("contrato MQTT · evento")
def test_un_permitido_publica_su_evento_con_la_llegada_que_creo(
    camaras, conexion: Connection, reloj, mqtt_servidor, escucha, broker_mqtt
) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    reloj.momento = hora(20, 7, 25, 30)

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    mensaje = escucha.esperar(EVENTO)
    assert (mensaje.qos, mensaje.retenido) == (1, False)
    assert mensaje.json() == {
        "evento_id": cuerpo["evento_id"],
        "dispositivo": "entrada",
        "resultado": "permitido",
        "motivo": None,
        "persona": {"id": str(ana), "nombre": ANA},
        "similitud": pytest.approx(1.0, abs=1e-6),
        "repetido": False,
        "asistencia": {"estado": "tarde", "minutos_tarde": 25},
        "hora": "2026-11-20T07:25:30-05:00",
    }
    assert retenidos(broker_mqtt, EVENTO) == {}  # los eventos no son retenidos


@pytest.mark.marca("contrato MQTT · evento")
def test_la_asistencia_solo_viaja_en_el_evento_que_creo_la_llegada(
    camaras, conexion: Connection, reloj, mqtt_servidor, escucha
) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    reloj.momento = hora(20, 6, 55)
    camara.enviar(CaraArmada(huella=eje(0)))
    reloj.momento = hora(20, 9, 0)
    camara.enviar(CaraArmada(huella=eje(0)))

    marcar(mqtt_servidor, escucha)
    assert [evento["asistencia"] for evento in eventos(escucha)] == [{"estado": "a_tiempo", "minutos_tarde": None}, None]


@pytest.mark.marca("contrato MQTT · evento")
def test_un_denegado_publica_su_evento_con_el_motivo(camaras, conexion: Connection, reloj, mqtt_servidor, escucha) -> None:
    camara = camaras()
    elena = armar.inscrita(conexion, ELENA, "1075000003", eje(0), activa=False)
    reloj.momento = hora(20, 7, 0)

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert escucha.esperar(EVENTO).json() == {
        "evento_id": cuerpo["evento_id"],
        "dispositivo": "entrada",
        "resultado": "denegado",
        "motivo": "inactiva",
        "persona": {"id": str(elena), "nombre": ELENA},
        "similitud": pytest.approx(1.0, abs=1e-6),
        "repetido": False,
        "asistencia": None,
        "hora": "2026-11-20T07:00:00-05:00",
    }


@pytest.mark.marca("RNF-01 · C3")
def test_un_desconocido_se_publica_sin_decir_a_quien_se_parece(
    camaras, conexion: Connection, reloj, mqtt_servidor, escucha
) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))
    reloj.momento = hora(20, 7, 0)

    cuerpo = camara.enviar(CaraArmada(huella=parecida(0.30))).json()

    mensaje = escucha.esperar(EVENTO)
    assert mensaje.json() == {
        "evento_id": cuerpo["evento_id"],
        "dispositivo": "entrada",
        "resultado": "desconocido",
        "motivo": "bajo_umbral",
        "persona": None,
        "similitud": pytest.approx(0.30, abs=1e-6),
        "repetido": False,
        "asistencia": None,
        "hora": "2026-11-20T07:00:00-05:00",
    }
    assert "Ana" not in mensaje.carga and str(ana) not in mensaje.carga


@pytest.mark.marca("contrato MQTT · evento")
def test_un_evento_que_se_deshace_no_se_publica(
    camaras, conexion: Connection, reloj, mqtt_servidor, escucha, monkeypatch: pytest.MonkeyPatch
) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    reloj.momento = hora(20, 7, 0)

    def falla(*_argumentos, **_opciones) -> None:
        raise RuntimeError("falla después de guardar el evento")

    # _registrar corre después de guardar el evento, dentro de la misma transacción.
    monkeypatch.setattr("accesia.rostros._registrar", falla)
    with pytest.raises(RuntimeError, match="después de guardar"):
        camara.enviar(CaraArmada(huella=eje(0)))

    marcar(mqtt_servidor, escucha)
    assert escucha.mensajes(EVENTO) == []
    assert armar.eventos(conexion) == []


@pytest.mark.marca("contrato MQTT · evento")
def test_si_la_transaccion_no_se_confirma_no_se_publica(
    app, camaras, conexion: Connection, candado_de_la_base, reloj, mqtt_servidor, escucha
) -> None:
    from accesia.db import obtener_conexion

    def conexion_que_no_confirma():
        with candado_de_la_base, conexion.begin_nested():
            yield conexion
            raise RuntimeError("la confirmación falló")  # después de la ruta, donde el servidor real confirma

    app.dependency_overrides[obtener_conexion] = conexion_que_no_confirma
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    reloj.momento = hora(20, 7, 0)

    with pytest.raises(RuntimeError, match="confirmación"):
        camara.enviar(CaraArmada(huella=eje(0)))

    marcar(mqtt_servidor, escucha)
    assert escucha.mensajes(EVENTO) == []


@pytest.mark.marca("contrato MQTT · evento")
def test_sin_conexion_no_se_publica_ni_queda_para_despues(conectar_mqtt, escucha, caplog) -> None:
    # paho guardaría un mensaje QoS 1 y lo enviaría al reconectar: un permitido viejo abriría la puerta tarde.
    caplog.set_level(logging.WARNING, logger="accesia")
    descartados: list[bool] = []

    def antes(servidor) -> None:
        descartados.append(servidor.publicar(Publicacion(EVENTO, '{"resultado": "permitido"}', 1, False)))

    servidor = conectar_mqtt(antes=antes)
    marcar(servidor, escucha)

    assert descartados == [False]
    assert escucha.mensajes(EVENTO) == []
    assert "sin conexión con el broker" in caplog.text


# --- R4 · la repetición en MQTT ---


@pytest.mark.marca("R4 · dentro")
def test_la_repeticion_de_un_permitido_se_publica_para_abrir_otra_vez(
    camaras, conexion: Connection, reloj, mqtt_servidor, escucha
) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    reloj.momento = hora(20, 6, 55)
    camara.enviar(CaraArmada(huella=eje(0)))

    reloj.avanzar(30)
    camara.enviar(CaraArmada(huella=parecida(0.9)))

    escucha.esperar(EVENTO, lambda mensaje: mensaje.json()["repetido"])
    original, repetido = eventos(escucha)
    # El evento_id es el del original; la persona, la similitud y la hora son las de este recorte; sin asistencia.
    assert repetido == {
        **original,
        "similitud": pytest.approx(0.9, abs=1e-6),
        "repetido": True,
        "asistencia": None,
        "hora": "2026-11-20T06:55:30-05:00",
    }
    assert original["asistencia"] == {"estado": "a_tiempo", "minutos_tarde": None}


@pytest.mark.marca("R4 · denegado repetido")
def test_la_repeticion_de_un_denegado_no_se_publica(camaras, conexion: Connection, reloj, mqtt_servidor, escucha) -> None:
    camara = camaras()
    armar.inscrita(conexion, ELENA, "1075000003", eje(0), activa=False)
    reloj.momento = hora(20, 7, 0)
    camara.enviar(CaraArmada(huella=eje(0)))

    reloj.avanzar(30)
    assert camara.enviar(CaraArmada(huella=eje(0))).json()["repetido"] is True

    marcar(mqtt_servidor, escucha)
    assert [(evento["resultado"], evento["repetido"]) for evento in eventos(escucha)] == [("denegado", False)]


@pytest.mark.marca("contrato MQTT · repetido")
def test_solo_la_repeticion_de_un_permitido_se_publica(camaras, conexion: Connection, reloj, mqtt_servidor, escucha) -> None:
    entrada = camaras("entrada")
    salida = camaras("salida")
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    armar.inscrita(conexion, ELENA, "1075000003", eje(1), activa=False)
    reloj.momento = hora(20, 7, 0)
    entrada.enviar(CaraArmada(huella=eje(0)))
    salida.enviar(CaraArmada(huella=eje(1)))

    reloj.avanzar(30)
    entrada.enviar(CaraArmada(huella=eje(0)))
    salida.enviar(CaraArmada(huella=eje(1)))

    marcar(mqtt_servidor, escucha)
    assert [evento["repetido"] for evento in eventos(escucha, "accesia/entrada/evento")] == [False, True]
    assert [evento["repetido"] for evento in eventos(escucha, "accesia/salida/evento")] == [False]


# --- contrato MQTT · resumen ---


def resumen_vacio(fecha: str, momento: str) -> dict:
    return {
        "fecha": fecha,
        "asistentes": 0,
        "a_tiempo": 0,
        "tarde": 0,
        "sin_horario": 0,
        "desconocidos_hoy": 0,
        "ultima_llegada": None,
        "hora": momento,
    }


@pytest.mark.marca("contrato MQTT · resumen")
def test_al_conectarse_publica_el_resumen_del_dia_retenido(
    conexion: Connection, reloj, conectar_mqtt, escucha, broker_mqtt, administrador: dict
) -> None:
    reloj.momento = hora(20, 8, 20)
    clase = armar.clase_ia(conexion)
    armar.camara(conexion, "entrada")
    ana = armar.persona(conexion, "1075000001", ANA, horario_id=clase)
    bruno = armar.persona(conexion, "1075000002", BRUNO, horario_id=clase)
    david = armar.persona(conexion, "1075000004", DAVID)
    fabio = armar.persona(conexion, "1075000006", "Fabio Torres", horario_id=clase)
    registrar_llegada(conexion, david, hora(20, 7, 40, 5), "camara")
    registrar_llegada(conexion, ana, hora(20, 6, 58), "camara")
    registrar_llegada(conexion, bruno, hora(20, 7, 12), "camara")
    registrar_llegada(conexion, fabio, hora(20, 7, 5), "manual", registrado_por=administrador["id"])
    registrar_llegada(conexion, ana, hora(19, 7, 0), "camara")  # de ayer: no cuenta
    for momento in (hora(19, 23, 59, 59), hora(20, 8, 0), hora(20, 8, 15)):
        armar.evento(conexion, "entrada", None, "desconocido", "bajo_umbral", 0.2, fecha_hora=momento)

    conectar_mqtt()

    mensaje = escucha.esperar(RESUMEN)
    assert (mensaje.qos, mensaje.retenido) == (1, False)
    assert mensaje.json() == {
        "fecha": "2026-11-20",
        "asistentes": 4,
        "a_tiempo": 2,
        "tarde": 1,
        "sin_horario": 1,
        "desconocidos_hoy": 2,
        "ultima_llegada": {"nombre": DAVID, "hora": "2026-11-20T07:40:05-05:00"},
        "hora": "2026-11-20T08:20:00-05:00",
    }
    assert json.loads(retenidos(broker_mqtt, RESUMEN)[RESUMEN]) == mensaje.json()


@pytest.mark.marca("contrato MQTT · resumen")
def test_sin_llegadas_la_ultima_llegada_es_null(reloj, conectar_mqtt, escucha) -> None:
    reloj.momento = hora(20, 6, 0)

    conectar_mqtt()

    assert escucha.esperar(RESUMEN).json() == resumen_vacio("2026-11-20", "2026-11-20T06:00:00-05:00")


@pytest.mark.marca("contrato MQTT · resumen")
def test_cada_evento_guardado_publica_el_resumen(camaras, conexion: Connection, reloj, mqtt_servidor, escucha) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0), horario_id=armar.clase_ia(conexion))
    reloj.momento = hora(20, 7, 0)
    escucha.olvidar()

    camara.enviar(CaraArmada(huella=parecida(0.1)))  # desconocido
    camara.enviar(CaraArmada(huella=eje(0)))  # permitido
    reloj.avanzar(30)
    camara.enviar(CaraArmada(huella=eje(0)))  # repetición: no guarda evento ni publica resumen

    marcar(mqtt_servidor, escucha)
    resumenes = [mensaje.json() for mensaje in escucha.mensajes(RESUMEN)]
    assert [(r["desconocidos_hoy"], r["asistentes"]) for r in resumenes] == [(1, 0), (1, 1)]
    assert resumenes[-1]["ultima_llegada"] == {"nombre": ANA, "hora": "2026-11-20T07:00:00-05:00"}


@pytest.mark.marca("contrato MQTT · resumen")
def test_una_llegada_manual_publica_el_resumen(sesion: TestClient, conexion: Connection, reloj, mqtt_servidor, escucha) -> None:
    reloj.momento = hora(20, 10, 0)
    ana = armar.persona(conexion, horario_id=armar.clase_ia(conexion))
    escucha.olvidar()

    respuesta = sesion.post("/api/v1/asistencia", json={"persona_id": str(ana), "llegada": "2026-11-20T07:25:30-05:00"})

    assert respuesta.status_code == 201, respuesta.text
    resumen = escucha.esperar(RESUMEN).json()
    assert (resumen["asistentes"], resumen["tarde"]) == (1, 1)
    assert resumen["ultima_llegada"] == {"nombre": ANA, "hora": "2026-11-20T07:25:30-05:00"}


@pytest.mark.marca("contrato MQTT · resumen")
def test_el_resumen_periodico_cambia_de_dia_a_medianoche(reloj, mqtt_servidor, escucha) -> None:
    reloj.momento = hora(20, 23, 59, 58)
    escucha.olvidar()

    def resumen_del(fecha: str):
        # Espera en otro hilo, para que el bucle siga publicando. Sin tiempos fijos: en la CI el runner es más lento.
        return asyncio.to_thread(escucha.esperar, RESUMEN, lambda mensaje: mensaje.json()["fecha"] == fecha)

    async def dos_vueltas() -> None:
        tarea = asyncio.create_task(resumen_periodico(mqtt_servidor, intervalo_s=0.05))
        try:
            await resumen_del("2026-11-20")
            reloj.momento = hora(21, 0, 0, 2)
            await resumen_del("2026-11-21")
        finally:
            tarea.cancel()
            await asyncio.gather(tarea, return_exceptions=True)

    asyncio.run(dos_vueltas())

    marcar(mqtt_servidor, escucha)
    fechas = [mensaje.json()["fecha"] for mensaje in escucha.mensajes(RESUMEN)]
    assert "2026-11-20" in fechas and fechas[-1] == "2026-11-21"


# --- contrato API · salud ---


@pytest.mark.marca("contrato API · salud")
def test_la_salud_dice_mqtt_ok_con_el_broker_conectado(cliente: TestClient, url_base: str, mqtt_servidor) -> None:
    respuesta = cliente.get("/api/v1/salud")

    assert respuesta.status_code == 200
    validar("Salud", respuesta.json())
    assert (respuesta.json()["mqtt"], respuesta.json()["estado"]) == ("ok", "ok")


@pytest.mark.marca("contrato API · salud")
def test_la_salud_dice_sin_conexion_si_se_pierde_el_broker(cliente: TestClient, url_base: str, mqtt_servidor) -> None:
    mqtt_servidor.detener()

    respuesta = cliente.get("/api/v1/salud")

    assert (respuesta.json()["mqtt"], respuesta.json()["estado"]) == ("sin_conexion", "degradado")


# --- RF-10 · C3: en línea y estado de las cámaras desde MQTT ---

ESTADO_DE_LA_PLACA = {
    "perfil": "xiao_esp32c6",
    "firmware": "tinyml-xiao_esp32c6-1.0.0",
    "ip": "192.168.137.23",
    "rssi": -52,
    "libre_kb": 210,
    "sensor": "dht22",
    "antena": "interna",
    "segundos_encendida": 5321,
}


def ver_camara(sesion: TestClient, codigo: str = "entrada") -> dict:
    respuesta = sesion.get(f"/api/v1/dispositivos/{codigo}")
    assert respuesta.status_code == 200, respuesta.text
    validar("Dispositivo", respuesta.json())
    return respuesta.json()


@pytest.fixture
def placa(broker_mqtt) -> ClienteDePrueba:
    """La placa de la cámara entrada: usuario camara y su código como client id (la ACL lo exige)."""
    cliente = ClienteDePrueba(broker_mqtt, "camara", client_id="entrada").conectar()
    yield cliente
    cliente.cerrar()


@pytest.mark.marca("RF-10 · C3")
def test_en_linea_y_estado_salen_de_lo_que_publica_la_camara(
    sesion: TestClient, conexion: Connection, conectar_mqtt, placa
) -> None:
    armar.camara(conexion, "entrada")  # sin último contacto por HTTP
    placa.publicar("accesia/entrada/disponible", "online", retenido=True)
    placa.publicar("accesia/entrada/estado", json.dumps(ESTADO_DE_LA_PLACA), retenido=True, qos=0)

    conectar_mqtt()  # los recibe retenidos al suscribirse

    assert hasta(lambda: ver_camara(sesion)["estado"] is not None)
    camara = ver_camara(sesion)
    assert (camara["en_linea"], camara["estado"]) == (True, ESTADO_DE_LA_PLACA)

    placa.publicar("accesia/entrada/disponible", "offline", retenido=True)
    assert hasta(lambda: ver_camara(sesion)["en_linea"] is False)


@pytest.mark.marca("RF-10 · C3")
def test_el_estado_del_simulador_lleva_solo_sus_campos(sesion: TestClient, conexion: Connection, mqtt_servidor, placa) -> None:
    armar.camara(conexion, "entrada")
    simulador = {"firmware": "simulador-1.0.0", "ip": "192.168.137.1", "segundos_encendida": 12}

    placa.publicar("accesia/entrada/estado", json.dumps(simulador), qos=0)

    assert hasta(lambda: ver_camara(sesion)["estado"] == simulador)


@pytest.mark.marca("RF-10 · C3")
@pytest.mark.parametrize(
    "carga",
    [
        "no es json",
        "[1, 2]",
        json.dumps({**ESTADO_DE_LA_PLACA, "rssi": "fuerte"}),
        json.dumps({**ESTADO_DE_LA_PLACA, "ip": None}),
        json.dumps({**ESTADO_DE_LA_PLACA, "sensor": "dht99"}),
        json.dumps({**ESTADO_DE_LA_PLACA, "segundos_encendida": True}),
    ],
    ids=["no es JSON", "no es un objeto", "rssi de texto", "ip nula", "sensor desconocido", "booleano por número"],
)
def test_un_estado_que_no_cumple_se_descarta(
    sesion: TestClient, conexion: Connection, mqtt_servidor, placa, caplog, carga: str
) -> None:
    caplog.set_level(logging.WARNING, logger="accesia")
    armar.camara(conexion, "entrada")
    placa.publicar("accesia/entrada/estado", json.dumps(ESTADO_DE_LA_PLACA), qos=0)
    assert hasta(lambda: ver_camara(sesion)["estado"] == ESTADO_DE_LA_PLACA)

    placa.publicar("accesia/entrada/estado", carga, qos=0)

    assert hasta(lambda: "no cumple EstadoCamara" in caplog.text)
    assert ver_camara(sesion)["estado"] == ESTADO_DE_LA_PLACA  # queda el último válido


@pytest.mark.marca("RF-10 · C3")
def test_un_contacto_reciente_por_http_tambien_cuenta_como_en_linea(
    sesion: TestClient, conexion: Connection, reloj, mqtt_servidor, placa
) -> None:
    armar.camara(conexion, "entrada", ultimo_contacto=reloj.momento - timedelta(seconds=30))
    placa.publicar("accesia/entrada/disponible", "online")
    assert hasta(lambda: mqtt_servidor.en_linea("entrada"))

    placa.publicar("accesia/entrada/disponible", "offline")
    assert hasta(lambda: not mqtt_servidor.en_linea("entrada"))  # el servidor ya sabe que se desconectó

    assert ver_camara(sesion)["en_linea"] is True  # pero hizo contacto por HTTP hace 30 s


@pytest.mark.marca("RF-10 · C3")
def test_sin_broker_cuenta_solo_el_contacto_y_queda_el_ultimo_estado(
    sesion: TestClient, conexion: Connection, mqtt_servidor, placa
) -> None:
    armar.camara(conexion, "entrada")
    placa.publicar("accesia/entrada/disponible", "online")
    placa.publicar("accesia/entrada/estado", json.dumps(ESTADO_DE_LA_PLACA), qos=0)
    assert hasta(lambda: ver_camara(sesion)["en_linea"] is True and ver_camara(sesion)["estado"] is not None)

    mqtt_servidor.detener()

    camara = ver_camara(sesion)
    assert (camara["en_linea"], camara["estado"]) == (False, ESTADO_DE_LA_PLACA)


@pytest.mark.marca("RF-10 · C3")
def test_la_disponibilidad_del_servidor_no_se_toma_por_una_camara(mqtt_servidor, placa) -> None:
    # El servidor también recibe su propio online en accesia/+/disponible, antes que lo que publica la placa.
    placa.publicar("accesia/entrada/disponible", "online")
    assert hasta(lambda: mqtt_servidor.en_linea("entrada"))

    assert mqtt_servidor.en_linea("servidor") is False
