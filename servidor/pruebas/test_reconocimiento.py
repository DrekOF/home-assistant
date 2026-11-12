"""
Nombre: test_reconocimiento.py
Descripción: Pruebas del reconocimiento con la visión armada y PostgreSQL real: R1, R2, R3, R4 (sin MQTT), R7 al reconocer, RF-05 · C1 y C2, y RNF-01 · C3 para los desconocidos.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import logging

import armar
import numpy as np
import pytest
from sqlalchemy import Connection, text
from vision_falsa import CaraArmada, eje, parecida

ANA = "Ana María Gómez"
BRUNO = "Bruno Díaz"
ELENA = "Elena Ruiz"


def _resultado(respuesta) -> tuple:
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    return cuerpo["resultado"], cuerpo["motivo"]


# --- R1 · Umbral de similitud ---


# 0,363 en float32 menos un paso: lo que puede dar pgvector, que calcula en float32, para una similitud de 0,363.
UMBRAL_EN_FLOAT32 = float(np.nextafter(np.float32(0.363), np.float32(0)))


@pytest.mark.marca("R1 · igual al umbral")
@pytest.mark.parametrize("similitud", [0.363, UMBRAL_EN_FLOAT32], ids=["0,363", "0,363 menos un paso de float32"])
def test_igual_al_umbral_coincide(camaras, conexion: Connection, similitud: float) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))

    cuerpo = camara.enviar(CaraArmada(huella=parecida(similitud))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("permitido", None)
    assert cuerpo["persona"] == {"id": str(ana), "nombre": ANA}
    assert cuerpo["similitud"] == pytest.approx(0.363, abs=1e-6)


@pytest.mark.marca("R1 · bajo el umbral")
def test_bajo_el_umbral_es_desconocido_sin_persona(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))

    cuerpo = camara.enviar(CaraArmada(huella=parecida(0.362))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["persona"]) == ("desconocido", "bajo_umbral", None)
    assert cuerpo["similitud"] == pytest.approx(0.362, abs=1e-6)
    [evento] = armar.eventos(conexion)
    assert (evento.resultado, evento.motivo, evento.persona_id) == ("desconocido", "bajo_umbral", None)


@pytest.mark.marca("R1 · base vacía")
def test_sin_muestras_es_desconocido_con_similitud_nula(camaras, conexion: Connection) -> None:
    camara = camaras()

    cuerpo = camara.enviar(CaraArmada()).json()

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["persona"], cuerpo["similitud"]) == (
        "desconocido",
        "bajo_umbral",
        None,
        None,
    )
    [evento] = armar.eventos(conexion)
    assert (evento.resultado, evento.similitud) == ("desconocido", None)


# --- R2 · La muestra más parecida ---


@pytest.mark.marca("R2 · varias muestras")
def test_cuenta_la_muestra_mas_parecida_de_la_persona(camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", parecida(0.30, libre=1), parecida(0.50, libre=2))

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert cuerpo["resultado"] == "permitido"
    assert cuerpo["persona"]["id"] == str(ana)
    assert cuerpo["similitud"] == pytest.approx(0.50, abs=1e-6)


@pytest.mark.marca("R2 · dos personas")
def test_entre_dos_personas_gana_la_mas_parecida(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", parecida(0.45, libre=1))
    bruno = armar.inscrita(conexion, BRUNO, "1075000002", parecida(0.48, libre=2))

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert cuerpo["persona"] == {"id": str(bruno), "nombre": BRUNO}
    assert cuerpo["similitud"] == pytest.approx(0.48, abs=1e-6)


# --- R3 · Estado de la persona ---


@pytest.mark.marca("R3 · inactiva")
def test_inactiva_es_denegado_por_inactiva(camaras, conexion: Connection) -> None:
    camara = camaras()
    elena = armar.inscrita(conexion, ELENA, "1075000003", parecida(0.70), activa=False)

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("denegado", "inactiva")
    assert cuerpo["persona"] == {"id": str(elena), "nombre": ELENA}
    assert cuerpo["similitud"] == pytest.approx(0.70, abs=1e-6)


@pytest.mark.marca("R3 · sin consentimiento")
def test_activo_con_huellas_y_sin_consentimiento_es_denegado(camaras, conexion: Connection) -> None:
    camara = camaras()
    # Estado armado directamente en la base: la API borraría las huellas al revocar.
    bruno = armar.inscrita(conexion, BRUNO, "1075000002", eje(0), con_consentimiento=False)

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("denegado", "sin_consentimiento")
    assert cuerpo["persona"]["id"] == str(bruno)


@pytest.mark.marca("R3 · las dos")
def test_inactiva_y_sin_consentimiento_gana_inactiva(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ELENA, "1075000003", eje(0), activa=False, con_consentimiento=False)

    assert _resultado(camara.enviar(CaraArmada(huella=eje(0)))) == ("denegado", "inactiva")


@pytest.mark.marca("R3 · todo bien")
def test_activa_y_con_consentimiento_es_permitido(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))

    assert _resultado(camara.enviar(CaraArmada(huella=eje(0)))) == ("permitido", None)


@pytest.mark.marca("R3 · revocado de punta a punta")
def test_quien_revoca_por_la_api_vuelve_como_desconocido(sesion, camaras, conexion: Connection) -> None:
    camara = camaras()
    bruno = armar.inscrita(conexion, BRUNO, "1075000002", eje(0), parecida(0.9))
    armar.inscrita(conexion, ANA, "1075000001", eje(7))  # nadie más se le parece
    assert _resultado(camara.enviar(CaraArmada(huella=eje(0)))) == ("permitido", None)

    assert sesion.delete(f"/api/v1/personas/{bruno}/consentimiento").status_code == 204
    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["persona"]) == ("desconocido", "bajo_umbral", None)
    assert armar.contar(conexion, "rostro", bruno) == 0


# --- R4 · Ventana de repetición (la publicación en MQTT es del Día 3) ---


@pytest.mark.marca("R4 · dentro")
def test_la_misma_persona_dentro_de_la_ventana_es_repeticion(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    primero = camara.enviar(CaraArmada(huella=eje(0))).json()

    reloj.avanzar(30)
    segundo = camara.enviar(CaraArmada(huella=parecida(0.9))).json()

    assert (segundo["resultado"], segundo["repetido"]) == ("permitido", True)
    assert segundo["evento_id"] == primero["evento_id"]
    assert segundo["persona"] == primero["persona"]
    assert segundo["mensaje"] == primero["mensaje"]
    assert segundo["similitud"] == pytest.approx(0.9, abs=1e-6)  # la de este recorte
    assert len(armar.eventos(conexion)) == 1


@pytest.mark.marca("R4 · denegado repetido")
def test_un_denegado_dentro_de_la_ventana_tambien_es_repeticion(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, ELENA, "1075000003", eje(0), activa=False)
    primero = camara.enviar(CaraArmada(huella=eje(0))).json()

    reloj.avanzar(30)
    segundo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (segundo["resultado"], segundo["motivo"], segundo["repetido"]) == ("denegado", "inactiva", True)
    assert segundo["evento_id"] == primero["evento_id"]
    assert len(armar.eventos(conexion)) == 1


@pytest.mark.marca("R4 · límite")
def test_a_los_60_segundos_ya_es_evento_nuevo(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    primero = camara.enviar(CaraArmada(huella=eje(0))).json()

    reloj.avanzar(60)
    segundo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert segundo["repetido"] is False
    assert segundo["evento_id"] != primero["evento_id"]
    assert len(armar.eventos(conexion)) == 2


@pytest.mark.marca("R4 · otra cámara")
def test_en_otra_camara_es_evento_nuevo(camaras, conexion: Connection, reloj) -> None:
    entrada, salida = camaras("entrada"), camaras("salida")
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    entrada.enviar(CaraArmada(huella=eje(0)))

    reloj.avanzar(30)
    cuerpo = salida.enviar(CaraArmada(huella=eje(0))).json()

    assert cuerpo["repetido"] is False
    assert [evento.dispositivo_codigo for evento in armar.eventos(conexion)] == ["entrada", "salida"]


@pytest.mark.marca("R4 · cambia el resultado")
def test_si_cambia_el_resultado_es_evento_nuevo(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    elena = armar.inscrita(conexion, ELENA, "1075000003", eje(0), activa=False)
    assert _resultado(camara.enviar(CaraArmada(huella=eje(0)))) == ("denegado", "inactiva")

    conexion.execute(text("UPDATE persona SET activa = true WHERE id = :id"), {"id": elena})
    reloj.avanzar(20)
    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["repetido"]) == ("permitido", False)
    assert [evento.resultado for evento in armar.eventos(conexion)] == ["denegado", "permitido"]


@pytest.mark.marca("R4 · desconocidos")
def test_dos_desconocidos_seguidos_son_dos_eventos(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))
    primero = camara.enviar(CaraArmada(huella=eje(3))).json()

    reloj.avanzar(10)
    segundo = camara.enviar(CaraArmada(huella=eje(3))).json()

    assert (primero["resultado"], segundo["resultado"]) == ("desconocido", "desconocido")
    assert segundo["repetido"] is False
    assert segundo["evento_id"] != primero["evento_id"]
    assert len(armar.eventos(conexion)) == 2


# --- R7 al reconocer (sin inscripción activa) ---


@pytest.mark.marca("R7 · reconocer con dos caras")
def test_con_dos_caras_se_usa_la_mas_grande(camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))
    armar.inscrita(conexion, BRUNO, "1075000002", eje(1))

    cuerpo = camara.enviar(CaraArmada(alto=90, huella=eje(1)), CaraArmada(alto=140, huella=eje(0))).json()

    assert cuerpo["resultado"] == "permitido"
    assert cuerpo["persona"]["id"] == str(ana)


@pytest.mark.marca("R7 · reconocer pequeña")
def test_una_cara_de_60_px_se_descarta_sin_evento(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))

    cuerpo = camara.enviar(CaraArmada(alto=60, huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["persona"], cuerpo["evento_id"]) == (
        "descartado",
        "cara_pequena",
        None,
        None,
    )
    assert armar.eventos(conexion) == []


@pytest.mark.marca("R7 · reconocer con tolerancia")
def test_una_cara_de_70_px_se_reconoce(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))

    assert _resultado(camara.enviar(CaraArmada(alto=70, huella=eje(0)))) == ("permitido", None)


@pytest.mark.marca("R7 · reconocer sin cara")
@pytest.mark.parametrize("caras", [[], [CaraArmada(puntaje=0.85)]], ids=["ninguna", "puntaje bajo"])
def test_sin_cara_de_puntaje_suficiente_se_descarta(camaras, conexion: Connection, caras: list) -> None:
    camara = camaras()

    cuerpo = camara.enviar(*caras).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("descartado", "sin_cara")
    assert armar.eventos(conexion) == []


# --- RF-05 · Registro de accesos ---


@pytest.mark.marca("RF-05 · C1")
def test_permitido_denegado_y_desconocido_guardan_su_evento(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))
    elena = armar.inscrita(conexion, ELENA, "1075000003", eje(1), activa=False)

    respuestas = [
        camara.enviar(CaraArmada(huella=eje(0))).json(),
        camara.enviar(CaraArmada(huella=eje(1))).json(),
        camara.enviar(CaraArmada(huella=eje(2))).json(),
    ]

    eventos = armar.eventos(conexion)
    assert [(e.resultado, e.motivo, e.persona_id) for e in eventos] == [
        ("permitido", None, ana),
        ("denegado", "inactiva", elena),
        ("desconocido", "bajo_umbral", None),
    ]
    assert [str(e.id) for e in eventos] == [r["evento_id"] for r in respuestas]
    assert all(e.dispositivo_codigo == "entrada" and e.fecha_hora == reloj.momento for e in eventos)
    assert eventos[0].similitud == pytest.approx(1.0, abs=1e-6)


@pytest.mark.marca("RF-05 · C2")
def test_descartados_repeticiones_e_inscripcion_no_guardan_evento(sesion, camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))
    camara.enviar()  # sin cara
    camara.enviar(CaraArmada(alto=50))  # cara pequeña
    assert armar.eventos(conexion) == []

    camara.enviar(CaraArmada(huella=eje(0)))
    camara.enviar(CaraArmada(huella=eje(0)))  # repetición de R4
    assert len(armar.eventos(conexion)) == 1

    assert sesion.post("/api/v1/inscripciones", json={"persona_id": str(ana), "dispositivo": "entrada"}).status_code == 201
    assert camara.enviar(CaraArmada(huella=eje(0))).json()["resultado"] == "muestra_aceptada"
    assert len(armar.eventos(conexion)) == 1


# --- RNF-01 · C3: nunca se dice a quién se parece un desconocido ---


@pytest.mark.marca("RNF-01 · C3")
def test_un_desconocido_no_nombra_a_quien_se_parece(camaras, conexion: Connection, caplog) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))
    caplog.set_level(logging.DEBUG)

    respuesta = camara.enviar(CaraArmada(huella=parecida(0.30)))

    cuerpo = respuesta.json()
    assert (cuerpo["resultado"], cuerpo["persona"]) == ("desconocido", None)
    for texto in (respuesta.text, caplog.text):
        assert "Ana" not in texto and str(ana) not in texto
    [evento] = armar.eventos(conexion)
    assert evento.persona_id is None
