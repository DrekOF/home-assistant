"""
Nombre: test_contrato_camara.py
Descripción: Pruebas del contrato cámara → servidor (specs/contratos/api-dispositivo.md): cada fila de las tablas de resultados y de errores, el orden de las comprobaciones y el último contacto.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import itertools

import armar
import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from vision_falsa import JPEG, CaraArmada, eje

from accesia.rostros import LIMITE_BYTES, ControlDeRitmo

ANA = "Ana María Gómez"
CAMPOS = {"modo", "resultado", "motivo", "persona", "similitud", "repetido", "evento_id", "inscripcion", "mensaje", "hora"}


def _respuesta(respuesta) -> dict:
    """Una respuesta 200 que cumple RespuestaRostro, con todos sus campos y la hora de Colombia (R8)."""
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    validar("RespuestaRostro", cuerpo)
    assert set(cuerpo) == CAMPOS
    assert cuerpo["hora"].endswith("-05:00")
    return cuerpo


def _error(respuesta, estado: int, codigo: str) -> dict:
    assert respuesta.status_code == estado, respuesta.text
    cuerpo = respuesta.json()
    validar("Error", cuerpo)
    assert cuerpo["codigo"] == codigo
    return cuerpo


def _ultimo_contacto(conexion: Connection, codigo: str = "entrada"):
    return conexion.execute(
        text("SELECT ultimo_contacto FROM dispositivo WHERE codigo = :codigo"), {"codigo": codigo}
    ).scalar_one()


def _jpeg_de(tamano: int) -> bytes:
    """Un JPEG válido de exactamente ese tamaño: el decodificador ignora lo que viene después del final."""
    assert tamano >= len(JPEG)
    return JPEG + b"\0" * (tamano - len(JPEG))


# --- Resultados ---


@pytest.mark.marca("contrato cámara · permitido")
def test_permitido(camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001", eje(0))

    cuerpo = _respuesta(camara.enviar(CaraArmada(huella=eje(0))))

    assert (cuerpo["modo"], cuerpo["resultado"], cuerpo["motivo"]) == ("reconocer", "permitido", None)
    assert cuerpo["persona"] == {"id": str(ana), "nombre": ANA}
    assert (cuerpo["repetido"], cuerpo["inscripcion"]) == (False, None)
    assert cuerpo["evento_id"] is not None
    assert cuerpo["mensaje"] == "Hola, Ana. Puedes pasar"


@pytest.mark.marca("contrato cámara · denegado")
@pytest.mark.parametrize(
    ("activa", "con_consentimiento", "motivo", "mensaje"),
    [
        (False, True, "inactiva", "Acceso denegado: persona inactiva"),
        (True, False, "sin_consentimiento", "Acceso denegado: falta el consentimiento"),
    ],
)
def test_denegado(camaras, conexion: Connection, activa: bool, con_consentimiento: bool, motivo: str, mensaje: str) -> None:
    camara = camaras()
    persona = armar.inscrita(conexion, ANA, "1075000001", eje(0), activa=activa, con_consentimiento=con_consentimiento)

    cuerpo = _respuesta(camara.enviar(CaraArmada(huella=eje(0))))

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["mensaje"]) == ("denegado", motivo, mensaje)
    assert cuerpo["persona"]["id"] == str(persona)
    assert cuerpo["evento_id"] is not None


@pytest.mark.marca("contrato cámara · desconocido")
def test_desconocido(camaras, conexion: Connection) -> None:
    camara = camaras()
    armar.inscrita(conexion, ANA, "1075000001", eje(0))

    cuerpo = _respuesta(camara.enviar(CaraArmada(huella=eje(1))))

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["persona"]) == ("desconocido", "bajo_umbral", None)
    assert cuerpo["similitud"] == pytest.approx(0.0, abs=1e-6)
    assert (cuerpo["evento_id"] is not None, cuerpo["mensaje"]) == (True, "No te reconozco")


@pytest.mark.marca("contrato cámara · descartado")
@pytest.mark.parametrize(
    ("caras", "motivo", "mensaje"),
    [([], "sin_cara", "No veo una cara"), ([CaraArmada(alto=63)], "cara_pequena", "Acércate a la cámara")],
)
def test_descartado(camaras, conexion: Connection, caras: list, motivo: str, mensaje: str) -> None:
    camara = camaras()

    cuerpo = _respuesta(camara.enviar(*caras))

    assert (cuerpo["resultado"], cuerpo["motivo"], cuerpo["mensaje"]) == ("descartado", motivo, mensaje)
    assert (cuerpo["persona"], cuerpo["similitud"], cuerpo["evento_id"], cuerpo["repetido"]) == (None, None, None, False)
    assert armar.eventos(conexion) == []


@pytest.mark.marca("contrato cámara · muestra_aceptada")
def test_muestra_aceptada(sesion: TestClient, camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001")
    inscripcion = sesion.post("/api/v1/inscripciones", json={"persona_id": str(ana), "dispositivo": "entrada"}).json()

    cuerpo = _respuesta(camara.enviar(CaraArmada()))

    assert (cuerpo["modo"], cuerpo["resultado"], cuerpo["motivo"]) == ("inscribir", "muestra_aceptada", None)
    assert cuerpo["persona"] == {"id": str(ana), "nombre": ANA}
    assert (cuerpo["similitud"], cuerpo["evento_id"], cuerpo["repetido"]) == (None, None, False)
    assert cuerpo["inscripcion"] == {
        "id": inscripcion["id"],
        "muestras": 1,
        "requeridas": 5,
        "estado": "activa",
        "vence": inscripcion["vence"],
    }
    assert cuerpo["mensaje"] == "Muestra 1 de 5"


@pytest.mark.marca("contrato cámara · muestra_rechazada")
@pytest.mark.parametrize(
    ("caras", "motivo", "mensaje"),
    [
        ([], "sin_cara", "No veo una cara"),
        ([CaraArmada(), CaraArmada(x=150)], "varias_caras", "Que se vea una sola cara"),
        ([CaraArmada(alto=60)], "cara_pequena", "Acércate a la cámara"),
        ([CaraArmada(nitidez=59.9)], "borrosa", "Imagen borrosa: no te muevas"),
        ([CaraArmada(huella=eje(5))], "parece_otra_persona", "Se parece a otra persona inscrita"),
    ],
)
def test_muestra_rechazada(sesion: TestClient, camaras, conexion: Connection, caras: list, motivo: str, mensaje: str) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001")
    armar.inscrita(conexion, "Bruno Díaz", "1075000002", eje(5))
    sesion.post("/api/v1/inscripciones", json={"persona_id": str(ana), "dispositivo": "entrada"})

    cuerpo = _respuesta(camara.enviar(*caras))

    assert (cuerpo["modo"], cuerpo["resultado"], cuerpo["motivo"], cuerpo["mensaje"]) == (
        "inscribir",
        "muestra_rechazada",
        motivo,
        mensaje,
    )
    assert cuerpo["persona"] == {"id": str(ana), "nombre": ANA}
    assert (cuerpo["similitud"], cuerpo["evento_id"]) == (None, None)
    assert cuerpo["inscripcion"]["muestras"] == 0


@pytest.mark.marca("contrato cámara · muestra_rechazada")
def test_muestra_rechazada_distinta_de_la_primera(sesion: TestClient, camaras, conexion: Connection) -> None:
    camara = camaras()
    ana = armar.inscrita(conexion, ANA, "1075000001")
    sesion.post("/api/v1/inscripciones", json={"persona_id": str(ana), "dispositivo": "entrada"})
    camara.enviar(CaraArmada(huella=eje(0)))

    cuerpo = _respuesta(camara.enviar(CaraArmada(huella=eje(1))))

    assert (cuerpo["motivo"], cuerpo["mensaje"]) == ("distinta_de_la_primera", "No se parece a la primera muestra")
    assert cuerpo["inscripcion"]["muestras"] == 1


# --- Errores ---


@pytest.mark.marca("contrato cámara · 401")
def test_token_que_falta_no_corresponde_o_camara_que_no_existe_dan_el_mismo_401(
    cliente: TestClient, camaras, conexion: Connection
) -> None:
    camara = camaras()
    otra = camaras("salida")
    ruta = camara.ruta
    casos = {
        "sin token": cliente.post(ruta, content=JPEG, headers={"Content-Type": "image/jpeg"}),
        "sin Bearer": cliente.post(ruta, content=JPEG, headers={"Authorization": camara.token, "Content-Type": "image/jpeg"}),
        "token de otra cámara": camara.enviar(CaraArmada(), token=otra.token),
        "token inventado": camara.enviar(CaraArmada(), token="no-es-el-token"),
        "cámara que no existe": cliente.post(
            "/api/v1/dispositivos/no-existe/rostros",
            content=JPEG,
            headers={"Authorization": f"Bearer {camara.token}", "Content-Type": "image/jpeg"},
        ),
    }

    cuerpos = [_error(respuesta, 401, "token_invalido") for respuesta in casos.values()]
    assert all(cuerpo == cuerpos[0] for cuerpo in cuerpos), "Los 401 no deben decir cuál de las tres pasó"
    assert _ultimo_contacto(conexion) is None
    assert _ultimo_contacto(conexion, "salida") is None


@pytest.mark.marca("contrato cámara · 403")
def test_camara_desactivada_con_token_valido_da_403(camaras, conexion: Connection, reloj) -> None:
    camara = camaras(activo=False)

    _error(camara.enviar(CaraArmada()), 403, "dispositivo_inactivo")

    assert _ultimo_contacto(conexion) == reloj.momento


@pytest.mark.marca("contrato cámara · 413")
def test_mas_de_100_kb_da_413_y_100_kb_justos_se_aceptan(camaras) -> None:
    camara = camaras()
    assert LIMITE_BYTES == 102_400

    _error(camara.enviar(datos=_jpeg_de(LIMITE_BYTES + 1)), 413, "imagen_grande")
    assert _respuesta(camara.enviar(datos=_jpeg_de(LIMITE_BYTES)))["resultado"] == "descartado"


@pytest.mark.marca("contrato cámara · 413")
def test_sin_content_length_tambien_corta_en_100_kb(camaras) -> None:
    camara = camaras()
    datos = _jpeg_de(LIMITE_BYTES + 1)

    def por_partes():
        for inicio in range(0, len(datos), 8192):
            yield datos[inicio : inicio + 8192]

    respuesta = camara.cliente.post(
        camara.ruta, content=por_partes(), headers={"Authorization": f"Bearer {camara.token}", "Content-Type": "image/jpeg"}
    )

    _error(respuesta, 413, "imagen_grande")


@pytest.mark.marca("contrato cámara · 415")
@pytest.mark.parametrize("tipo", ["image/png", "application/octet-stream", ""])
def test_un_cuerpo_que_no_es_image_jpeg_da_415(camaras, tipo: str) -> None:
    camara = camaras()

    _error(camara.enviar(CaraArmada(), tipo=tipo), 415, "tipo_no_soportado")


@pytest.mark.marca("contrato cámara · 415")
def test_image_jpeg_con_parametros_se_acepta(camaras) -> None:
    camara = camaras()

    assert _respuesta(camara.enviar(tipo="Image/JPEG; q=0.8"))["resultado"] == "descartado"


@pytest.mark.marca("contrato cámara · 422")
@pytest.mark.parametrize(
    "datos",
    [b"", b"no es una imagen", JPEG[:40], b"\x89PNG\r\n\x1a\n" + b"\0" * 64],
    ids=["vacío", "texto", "JPEG cortado", "PNG"],
)
def test_un_jpeg_que_no_se_puede_leer_da_422(camaras, datos: bytes) -> None:
    camara = camaras()

    _error(camara.enviar(datos=datos), 422, "imagen_invalida")
    assert camara.vision.imagenes == 0


@pytest.mark.marca("contrato cámara · 429")
def test_dos_recortes_en_menos_de_0_8_s_dan_429(app, camaras) -> None:
    camara = camaras()
    instantes = iter([0.0, 0.5, 0.8, 1.5, 1.59, 1.6])
    app.state.ritmo = ControlDeRitmo(reloj=instantes.__next__)

    primero = camara.enviar()
    muy_pronto = camara.enviar()  # 0,5 s después del primero
    a_tiempo = camara.enviar()  # 0,8 s después del primero: el 429 no movió el reloj
    pronto = camara.enviar()  # 0,7 s después del aceptado en 0,8 s
    casi = camara.enviar()  # 0,79 s después
    justo = camara.enviar()  # 0,8 s después

    assert _respuesta(primero)["resultado"] == "descartado"
    _error(muy_pronto, 429, "demasiadas_peticiones")
    assert muy_pronto.headers["Retry-After"] == "1"
    assert a_tiempo.status_code == 200
    assert (pronto.status_code, casi.status_code, justo.status_code) == (429, 429, 200)


@pytest.mark.marca("contrato cámara · 429")
def test_el_ritmo_se_cuenta_por_camara(app, camaras) -> None:
    entrada, salida = camaras("entrada"), camaras("salida")
    app.state.ritmo = ControlDeRitmo(reloj=itertools.repeat(5.0).__next__)

    assert entrada.enviar().status_code == 200
    assert salida.enviar().status_code == 200
    assert entrada.enviar().status_code == 429


# --- Orden de las comprobaciones y efectos ---


@pytest.mark.marca("contrato cámara · orden")
def test_las_comprobaciones_van_en_orden(app, camaras) -> None:
    activa = camaras("entrada")
    inactiva = camaras("salida", activo=False)
    grande = _jpeg_de(LIMITE_BYTES + 1)

    # token antes que todo; cámara inactiva antes que el tipo; tipo antes que el tamaño; tamaño antes que el ritmo
    assert activa.enviar(datos=b"x", token="malo", tipo="image/png").status_code == 401
    assert inactiva.enviar(datos=grande, tipo="image/png").status_code == 403
    assert activa.enviar(datos=grande, tipo="image/png").status_code == 415
    app.state.ritmo = ControlDeRitmo(reloj=itertools.repeat(9.0).__next__)
    assert activa.enviar().status_code == 200
    assert activa.enviar(datos=grande).status_code == 413
    # ritmo antes que la imagen
    assert activa.enviar(datos=b"no es un jpeg").status_code == 429


@pytest.mark.marca("contrato cámara · último contacto")
def test_cada_peticion_con_token_valido_actualiza_el_ultimo_contacto(camaras, conexion: Connection, reloj) -> None:
    camara = camaras()

    for respuesta_esperada, envio in [
        (200, lambda: camara.enviar(CaraArmada())),
        (415, lambda: camara.enviar(tipo="image/png")),
        (413, lambda: camara.enviar(datos=_jpeg_de(LIMITE_BYTES + 1))),
        (422, lambda: camara.enviar(datos=b"no es un jpeg")),
    ]:
        reloj.avanzar(10)
        assert envio().status_code == respuesta_esperada
        assert _ultimo_contacto(conexion) == reloj.momento


@pytest.mark.marca("contrato cámara · último contacto")
def test_la_camara_queda_en_linea_despues_de_enviar(sesion: TestClient, camaras) -> None:
    camara = camaras()
    camara.enviar()

    assert sesion.get("/api/v1/dispositivos/entrada").json()["en_linea"] is True
