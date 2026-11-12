"""
Nombre: test_inscripcion.py
Descripción: Pruebas de la inscripción con la visión armada y PostgreSQL real: R7 al inscribir (en el orden de la regla), R9, RF-02 · C4, el contrato de abrirInscripcion, verInscripcion y cancelarInscripcion, y RNF-01 · C3 para parece_otra_persona.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import logging
from datetime import datetime, timedelta
from uuid import uuid4

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from vision_falsa import CaraArmada, eje, parecida

from accesia.tiempo import ahora

ANA = "Ana María Gómez"
BRUNO = "Bruno Díaz"


def _abrir(sesion: TestClient, persona_id, dispositivo: str = "entrada"):
    return sesion.post("/api/v1/inscripciones", json={"persona_id": str(persona_id), "dispositivo": dispositivo})


def _inscripcion_de(sesion: TestClient, persona_id, dispositivo: str = "entrada") -> dict:
    respuesta = _abrir(sesion, persona_id, dispositivo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _fila(conexion: Connection, inscripcion_id):
    return conexion.execute(
        text("SELECT estado, muestras, requeridas, ultimo_motivo, vence, terminada FROM inscripcion WHERE id = :id"),
        {"id": inscripcion_id},
    ).one()


def _rostros_de(conexion: Connection, inscripcion_id) -> list:
    return conexion.execute(
        text("SELECT persona_id, fuente, calidad, modelo FROM rostro WHERE inscripcion_id = :id ORDER BY creado, id"),
        {"id": inscripcion_id},
    ).all()


@pytest.fixture
def ana(conexion: Connection):
    """Ana, con consentimiento vigente y sin huellas."""
    return armar.inscrita(conexion, ANA, "1075000001")


# --- R7 · Calidad de una muestra para inscribir ---


@pytest.mark.marca("R7 · válida")
def test_una_cara_valida_es_muestra_aceptada_y_se_guarda(sesion, camaras, conexion: Connection, ana) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(alto=120, nitidez=150)).json()

    assert (cuerpo["modo"], cuerpo["resultado"], cuerpo["motivo"]) == ("inscribir", "muestra_aceptada", None)
    assert cuerpo["persona"] == {"id": str(ana), "nombre": ANA}
    assert (cuerpo["similitud"], cuerpo["evento_id"], cuerpo["repetido"]) == (None, None, False)
    assert cuerpo["inscripcion"]["muestras"] == 1
    assert cuerpo["mensaje"] == "Muestra 1 de 5"
    [rostro] = _rostros_de(conexion, inscripcion["id"])
    assert (rostro.persona_id, rostro.fuente, rostro.modelo) == (ana, "simulador", "sface_2021dec")
    assert rostro.calidad == pytest.approx(150)


@pytest.mark.marca("R7 · sin cara")
@pytest.mark.parametrize("caras", [[], [CaraArmada(puntaje=0.85)]], ids=["pared", "puntaje bajo"])
def test_sin_cara_es_muestra_rechazada(sesion, camaras, conexion: Connection, ana, caras: list) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(*caras).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "sin_cara")
    fila = _fila(conexion, inscripcion["id"])
    assert (fila.muestras, fila.ultimo_motivo, fila.estado) == (0, "sin_cara", "activa")


@pytest.mark.marca("R7 · dos caras")
def test_dos_caras_es_varias_caras(sesion, camaras, ana) -> None:
    camara = camaras()
    _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(alto=120), CaraArmada(alto=100, x=150)).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "varias_caras")


@pytest.mark.marca("R7 · pequeña")
def test_una_cara_de_60_px_es_cara_pequena(sesion, camaras, ana) -> None:
    camara = camaras()
    _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(alto=60)).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "cara_pequena")


@pytest.mark.marca("R7 · tolerancia de tamaño")
def test_una_cara_de_70_px_con_buena_nitidez_se_acepta(sesion, camaras, ana) -> None:
    camara = camaras()
    _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(alto=70, nitidez=150)).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_aceptada", None)


@pytest.mark.marca("R7 · borrosa")
def test_nitidez_30_es_borrosa(sesion, camaras, conexion: Connection, ana) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(nitidez=30)).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "borrosa")
    assert _rostros_de(conexion, inscripcion["id"]) == []


@pytest.mark.marca("R7 · otra persona")
def test_si_se_parece_a_otra_persona_se_rechaza(sesion, camaras, conexion: Connection, ana) -> None:
    camara = camaras()
    armar.inscrita(conexion, BRUNO, "1075000002", parecida(0.60, libre=2))
    _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "parece_otra_persona")
    assert cuerpo["persona"] == {"id": str(ana), "nombre": ANA}


@pytest.mark.marca("R7 · se parece a las dos")
def test_aunque_se_parezca_mas_a_ella_misma_cuenta_la_otra(sesion, camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", parecida(0.80, libre=1))
    armar.inscrita(conexion, BRUNO, "1075000002", parecida(0.50, libre=2))
    _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "parece_otra_persona")


@pytest.mark.marca("R7 · la misma persona")
def test_si_se_parece_a_sus_propias_muestras_se_acepta(sesion, camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", parecida(0.80, libre=1), parecida(0.85, libre=2))
    _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_aceptada", None)


@pytest.mark.marca("R7 · primera muestra")
def test_la_primera_muestra_no_se_compara_con_nada_de_la_inscripcion(sesion, camaras, conexion: Connection, ana) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(CaraArmada(huella=eje(9))).json()

    assert (cuerpo["resultado"], cuerpo["inscripcion"]["muestras"]) == ("muestra_aceptada", 1)
    assert len(_rostros_de(conexion, inscripcion["id"])) == 1


@pytest.mark.marca("R7 · igual a la primera")
def test_la_segunda_muestra_parecida_a_la_primera_se_acepta(sesion, camaras, ana) -> None:
    camara = camaras()
    _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))

    cuerpo = camara.enviar(CaraArmada(huella=parecida(0.65))).json()

    assert (cuerpo["resultado"], cuerpo["inscripcion"]["muestras"]) == ("muestra_aceptada", 2)


@pytest.mark.marca("R7 · distinta de la primera")
def test_una_cara_distinta_de_la_primera_se_rechaza(sesion, camaras, conexion: Connection, ana) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))

    cuerpo = camara.enviar(CaraArmada(huella=parecida(0.20, libre=3))).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "distinta_de_la_primera")
    fila = _fila(conexion, inscripcion["id"])
    assert (fila.muestras, fila.ultimo_motivo) == (1, "distinta_de_la_primera")


@pytest.mark.marca("R7 · distinta de la primera")
def test_la_primera_es_la_mas_antigua_aunque_la_segunda_se_parezca(sesion, camaras, ana, reloj) -> None:
    camara = camaras()
    _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))
    reloj.avanzar(1)
    camara.enviar(CaraArmada(huella=parecida(0.70, libre=4)))
    reloj.avanzar(1)

    # Se parece a la segunda (0,70 × 0,40 + 0,71 × 0,92 ≈ 0,93) pero a la primera solo 0,40 ≥ 0,363: se acepta.
    assert camara.enviar(CaraArmada(huella=parecida(0.40, libre=4))).json()["resultado"] == "muestra_aceptada"
    # A la primera 0,30 < 0,363: se rechaza aunque a la segunda se parezca.
    cuerpo = camara.enviar(CaraArmada(huella=parecida(0.30, libre=4))).json()
    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", "distinta_de_la_primera")


@pytest.mark.marca("R7 · orden")
@pytest.mark.parametrize(
    ("caras", "motivo"),
    [
        ([CaraArmada(puntaje=0.5), CaraArmada(alto=40, puntaje=0.5, nitidez=1)], "sin_cara"),
        ([CaraArmada(alto=40, nitidez=1), CaraArmada(alto=40, x=150, nitidez=1)], "varias_caras"),
        ([CaraArmada(alto=40, nitidez=1, huella=eje(5))], "cara_pequena"),
        ([CaraArmada(nitidez=1, huella=eje(5))], "borrosa"),
        ([CaraArmada(huella=eje(5))], "parece_otra_persona"),
    ],
    ids=["sin_cara antes que todo", "varias antes que pequeña", "pequeña antes que borrosa", "borrosa antes que otra", "otra"],
)
def test_responde_el_primer_motivo_que_falla(sesion, camaras, conexion: Connection, ana, caras: list, motivo: str) -> None:
    camara = camaras()
    armar.inscrita(conexion, BRUNO, "1075000002", eje(5))  # cualquier cara eje(5) se parece a Bruno
    _inscripcion_de(sesion, ana)

    cuerpo = camara.enviar(*caras).json()

    assert (cuerpo["resultado"], cuerpo["motivo"]) == ("muestra_rechazada", motivo)


@pytest.mark.marca("R7 · orden")
def test_parece_otra_persona_va_antes_que_distinta_de_la_primera(sesion, camaras, conexion: Connection, ana) -> None:
    camara = camaras()
    armar.inscrita(conexion, BRUNO, "1075000002", eje(5))
    _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))

    cuerpo = camara.enviar(CaraArmada(huella=eje(5))).json()

    assert cuerpo["motivo"] == "parece_otra_persona"


# --- RNF-01 · C3: parece_otra_persona no dice a quién ---


@pytest.mark.marca("RNF-01 · C3")
def test_parece_otra_persona_no_nombra_a_la_otra(sesion, camaras, conexion: Connection, ana, caplog) -> None:
    camara = camaras()
    bruno = armar.inscrita(conexion, BRUNO, "1075000002", parecida(0.60, libre=2))
    _inscripcion_de(sesion, ana)
    caplog.set_level(logging.DEBUG)

    respuesta = camara.enviar(CaraArmada(huella=eje(0)))

    assert respuesta.json()["motivo"] == "parece_otra_persona"
    for texto in (respuesta.text, caplog.text):
        assert "Bruno" not in texto and str(bruno) not in texto


# --- R9 · Sesión de inscripción ---


@pytest.mark.marca("R9 · segunda en la misma cámara")
def test_una_segunda_inscripcion_en_la_misma_camara_da_409(sesion, camaras, conexion: Connection, ana) -> None:
    camaras()
    bruno = armar.inscrita(conexion, BRUNO, "1075000002")
    _inscripcion_de(sesion, ana)

    respuesta = _abrir(sesion, bruno)

    assert respuesta.status_code == 409
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "inscripcion_activa"


@pytest.mark.marca("R9 · sin consentimiento")
def test_sin_consentimiento_vigente_da_422(sesion, camaras, conexion: Connection) -> None:
    camaras()
    sin = armar.inscrita(conexion, BRUNO, "1075000002", con_consentimiento=False)

    respuesta = _abrir(sesion, sin)

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "sin_consentimiento"


@pytest.mark.marca("R9 · completa")
def test_con_cinco_muestras_queda_completada_y_la_camara_vuelve_a_reconocer(
    sesion, camaras, conexion: Connection, ana, reloj
) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)

    respuestas = [camara.enviar(CaraArmada(huella=parecida(0.9 + i / 100, libre=i + 1))).json() for i in range(5)]

    assert [r["resultado"] for r in respuestas] == ["muestra_aceptada"] * 5
    assert [r["inscripcion"]["muestras"] for r in respuestas] == [1, 2, 3, 4, 5]
    assert respuestas[-1]["inscripcion"]["estado"] == "completada"
    assert respuestas[-1]["mensaje"] == "Muestra 5 de 5: inscripción completa"
    fila = _fila(conexion, inscripcion["id"])
    assert (fila.estado, fila.muestras, fila.terminada) == ("completada", 5, reloj.momento)

    siguiente = camara.enviar(CaraArmada(huella=eje(0))).json()
    assert (siguiente["modo"], siguiente["resultado"], siguiente["inscripcion"]) == ("reconocer", "permitido", None)


@pytest.mark.marca("R9 · vence")
def test_pasados_121_s_vence_y_conserva_las_muestras(sesion, camaras, conexion: Connection, ana, reloj) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))
    camara.enviar(CaraArmada(huella=parecida(0.9)))

    reloj.avanzar(121)
    vista = sesion.get(f"/api/v1/inscripciones/{inscripcion['id']}").json()

    assert (vista["estado"], vista["muestras"]) == ("vencida", 2)
    assert armar.contar(conexion, "rostro", ana) == 2
    siguiente = camara.enviar(CaraArmada(huella=eje(0))).json()
    assert (siguiente["modo"], siguiente["resultado"]) == ("reconocer", "permitido")


@pytest.mark.marca("R9 · vence")
def test_la_siguiente_cara_tambien_vence_la_inscripcion(sesion, camaras, conexion: Connection, ana, reloj) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))

    reloj.avanzar(121)
    siguiente = camara.enviar(CaraArmada(huella=eje(0))).json()

    assert siguiente["modo"] == "reconocer"
    assert _fila(conexion, inscripcion["id"]).estado == "vencida"


@pytest.mark.marca("R9 · cancelar")
def test_la_web_cancela_la_inscripcion(sesion, camaras, conexion: Connection, ana, reloj) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))
    reloj.avanzar(5)

    assert sesion.delete(f"/api/v1/inscripciones/{inscripcion['id']}").status_code == 204

    vista = sesion.get(f"/api/v1/inscripciones/{inscripcion['id']}").json()
    assert (vista["estado"], vista["muestras"]) == ("cancelada", 1)
    assert vista["terminada"] == reloj.momento.isoformat()
    assert camara.enviar(CaraArmada(huella=eje(0))).json()["modo"] == "reconocer"


@pytest.mark.marca("R9 · otra cámara")
def test_con_inscripcion_en_entrada_salida_sigue_reconociendo(sesion, camaras, conexion: Connection, ana) -> None:
    camaras("entrada")
    salida = camaras("salida")
    armar.rostro(conexion, ana, huella=eje(0))
    _inscripcion_de(sesion, ana, "entrada")

    cuerpo = salida.enviar(CaraArmada(huella=eje(0))).json()

    assert (cuerpo["modo"], cuerpo["resultado"]) == ("reconocer", "permitido")


@pytest.mark.marca("R9 · vencida sin revisar")
def test_una_vencida_que_nadie_reviso_no_bloquea_la_camara(sesion, camaras, conexion: Connection, ana) -> None:
    camaras()
    # Se abrió hace 130 s y vencía a los 120 s; nadie la consultó ni llegó otra cara.
    vieja = armar.inscripcion(conexion, ana, "entrada", ahora() - timedelta(seconds=10), muestras=1)

    respuesta = _abrir(sesion, ana)

    assert respuesta.status_code == 201, respuesta.text
    fila = _fila(conexion, vieja)
    assert (fila.estado, fila.terminada) == ("vencida", fila.vence)


@pytest.mark.marca("R9 · revoca a mitad")
def test_al_revocar_a_mitad_se_cancela_y_la_siguiente_cara_se_reconoce(
    sesion, camaras, conexion: Connection, ana
) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))
    camara.enviar(CaraArmada(huella=parecida(0.9)))

    assert sesion.delete(f"/api/v1/personas/{ana}/consentimiento").status_code == 204

    assert _fila(conexion, inscripcion["id"]).estado == "cancelada"
    assert armar.contar(conexion, "rostro", ana) == 0
    siguiente = camara.enviar(CaraArmada(huella=eje(0))).json()
    assert (siguiente["modo"], siguiente["resultado"], siguiente["persona"]) == ("reconocer", "desconocido", None)


# --- RF-02 · C4 ---


@pytest.mark.marca("RF-02 · C4")
def test_sin_consentimiento_vigente_no_se_abre_ninguna_inscripcion(sesion, camaras, conexion: Connection) -> None:
    camaras()
    revocado = armar.inscrita(conexion, BRUNO, "1075000002")
    conexion.execute(text("UPDATE consentimiento SET revocado_en = now() WHERE persona_id = :id"), {"id": revocado})

    respuesta = _abrir(sesion, revocado)

    assert (respuesta.status_code, respuesta.json()["codigo"]) == (422, "sin_consentimiento")
    assert armar.contar(conexion, "inscripcion", revocado) == 0


# --- Contrato de la API: abrirInscripcion, verInscripcion y cancelarInscripcion ---


@pytest.mark.marca("contrato API · abrirInscripcion")
def test_abrir_responde_201_con_el_esquema_inscripcion(sesion, camaras, ana, reloj) -> None:
    camaras()

    respuesta = _abrir(sesion, ana)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    validar("Inscripcion", cuerpo)
    assert cuerpo["persona"] == {"id": str(ana), "nombre": ANA}
    assert (cuerpo["dispositivo"], cuerpo["estado"], cuerpo["muestras"], cuerpo["requeridas"]) == ("entrada", "activa", 0, 5)
    assert (cuerpo["ultimo_motivo"], cuerpo["terminada"]) == (None, None)
    assert cuerpo["creada"] == reloj.momento.isoformat()
    assert datetime.fromisoformat(cuerpo["vence"]) - datetime.fromisoformat(cuerpo["creada"]) == timedelta(seconds=120)
    assert cuerpo["vence"].endswith("-05:00")


@pytest.mark.marca("contrato API · abrirInscripcion")
def test_abrir_para_una_persona_o_camara_que_no_existe_da_404(sesion, camaras, ana) -> None:
    camaras()

    sin_persona = _abrir(sesion, uuid4())
    sin_camara = _abrir(sesion, ana, "no-existe")

    for respuesta in (sin_persona, sin_camara):
        assert respuesta.status_code == 404
        validar("Error", respuesta.json())
        assert respuesta.json()["codigo"] == "no_encontrado"


@pytest.mark.marca("contrato API · abrirInscripcion")
def test_abrir_en_una_camara_inactiva_da_422_validacion(sesion, camaras, conexion: Connection, ana) -> None:
    camaras(activo=False)

    respuesta = _abrir(sesion, ana)

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "La cámara está desactivada: actívala antes de inscribir.", "codigo": "validacion"}
    assert armar.contar(conexion, "inscripcion", ana) == 0


@pytest.mark.marca("contrato API · abrirInscripcion")
@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"persona_id": "no-es-uuid", "dispositivo": "entrada"}, {"persona_id": str(uuid4()), "dispositivo": "ENTRADA"}],
    ids=["vacío", "persona no uuid", "código inválido"],
)
def test_abrir_con_datos_que_no_sirven_da_422(sesion, cuerpo: dict) -> None:
    respuesta = sesion.post("/api/v1/inscripciones", json=cuerpo)

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "validacion"


@pytest.mark.marca("contrato API · verInscripcion")
def test_ver_muestra_el_avance_y_el_ultimo_motivo(sesion, camaras, ana) -> None:
    camara = camaras()
    inscripcion = _inscripcion_de(sesion, ana)
    camara.enviar(CaraArmada(huella=eje(0)))
    camara.enviar(CaraArmada(nitidez=10))

    respuesta = sesion.get(f"/api/v1/inscripciones/{inscripcion['id']}")

    assert respuesta.status_code == 200
    validar("Inscripcion", respuesta.json())
    assert (respuesta.json()["muestras"], respuesta.json()["ultimo_motivo"]) == (1, "borrosa")


@pytest.mark.marca("contrato API · verInscripcion")
@pytest.mark.parametrize("inscripcion_id", [str(uuid4()), "no-es-uuid"])
def test_ver_una_inscripcion_que_no_existe_da_404(sesion, inscripcion_id: str) -> None:
    respuesta = sesion.get(f"/api/v1/inscripciones/{inscripcion_id}")

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"


@pytest.mark.marca("contrato API · verInscripcion")
def test_ver_vence_la_inscripcion_si_ya_paso_su_hora(sesion, camaras, conexion: Connection, ana) -> None:
    camaras()
    vieja = armar.inscripcion(conexion, ana, "entrada", ahora() - timedelta(seconds=1))

    cuerpo = sesion.get(f"/api/v1/inscripciones/{vieja}").json()

    validar("Inscripcion", cuerpo)
    assert cuerpo["estado"] == "vencida"
    assert cuerpo["terminada"] == cuerpo["vence"]


@pytest.mark.marca("contrato API · cancelarInscripcion")
def test_cancelar_una_que_no_existe_da_404(sesion) -> None:
    for inscripcion_id in (str(uuid4()), "no-es-uuid"):
        respuesta = sesion.delete(f"/api/v1/inscripciones/{inscripcion_id}")
        assert (respuesta.status_code, respuesta.json()["codigo"]) == (404, "no_encontrado")


@pytest.mark.marca("contrato API · cancelarInscripcion")
def test_cancelar_una_terminada_da_409(sesion, camaras, conexion: Connection, ana) -> None:
    camaras()
    inscripcion = _inscripcion_de(sesion, ana)
    assert sesion.delete(f"/api/v1/inscripciones/{inscripcion['id']}").status_code == 204
    vencida = armar.inscripcion(conexion, ana, "entrada", ahora() - timedelta(seconds=1))

    for inscripcion_id in (inscripcion["id"], vencida):
        respuesta = sesion.delete(f"/api/v1/inscripciones/{inscripcion_id}")
        assert respuesta.status_code == 409
        validar("Error", respuesta.json())
        assert respuesta.json()["codigo"] == "inscripcion_terminada"
    assert _fila(conexion, vencida).estado == "vencida"
