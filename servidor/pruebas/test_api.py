"""
Nombre: test_api.py
Descripción: Pruebas «contrato API · salud» y «contrato API · error» (incluido el 405) contra specs/contratos/openapi.yaml.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
"""

import pytest
from esquemas import validar
from fastapi.testclient import TestClient

from accesia.main import crear_app


@pytest.mark.marca("contrato API · salud")
def test_salud_responde_con_el_esquema_salud(url_base: str) -> None:
    respuesta = TestClient(crear_app()).get("/api/v1/salud")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    validar("Salud", datos)
    assert datos["base"] == "ok"
    # Sin el arranque no hay cliente MQTT: el servidor queda degradado (con el broker, test_mqtt.py).
    assert datos["mqtt"] == "sin_conexion"
    assert datos["estado"] == "degradado"
    assert datos["hora"].endswith("-05:00"), "La hora va en ISO 8601 con la zona de Colombia (R8)."


@pytest.mark.marca("contrato API · error")
def test_un_error_de_validacion_usa_el_esquema_error() -> None:
    app = crear_app()

    @app.get("/prueba/validacion")
    def ruta_de_prueba(numero: int) -> dict[str, int]:
        return {"numero": numero}

    respuesta = TestClient(app).get("/prueba/validacion", params={"numero": "no-es-un-numero"})

    assert respuesta.status_code == 422
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "validacion"
    assert "numero" in respuesta.json()["detalle"]


@pytest.mark.marca("contrato API · error")
def test_una_ruta_que_no_existe_usa_el_esquema_error() -> None:
    respuesta = TestClient(crear_app()).get("/api/v1/no-existe")

    assert respuesta.status_code == 404
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "no_encontrado"


@pytest.mark.marca("contrato API · error")
def test_un_metodo_que_la_ruta_no_acepta_responde_metodo_no_permitido() -> None:
    respuesta = TestClient(crear_app()).delete("/api/v1/salud")

    assert respuesta.status_code == 405
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "metodo_no_permitido"
    assert "GET" in respuesta.headers["allow"], "El 405 conserva la cabecera Allow con los métodos que sí acepta."


@pytest.mark.marca("contrato API · error")
def test_un_error_interno_usa_el_esquema_error() -> None:
    app = crear_app()

    @app.get("/prueba/falla")
    def ruta_que_falla() -> None:
        raise RuntimeError("falla de prueba")

    respuesta = TestClient(app, raise_server_exceptions=False).get("/prueba/falla")

    assert respuesta.status_code == 500
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "error_interno"
