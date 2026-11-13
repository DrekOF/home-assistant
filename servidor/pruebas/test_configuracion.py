"""
Nombre: test_configuracion.py
Descripción: Pruebas de verConfiguracion (D-14): los valores de las reglas que usa el servidor, leídos del entorno, los modelos de detección y de huella, y la versión.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import pytest
from esquemas import validar
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from accesia import __version__
from accesia.config import configuracion

CONFIGURACION = "/api/v1/configuracion"


@pytest.mark.marca("contrato API · verConfiguracion")
def test_la_configuracion_trae_los_valores_que_usa_el_servidor(sesion: TestClient) -> None:
    conf = configuracion()

    respuesta = sesion.get(CONFIGURACION)

    assert respuesta.status_code == 200, respuesta.text
    validar("Configuracion", respuesta.json())
    assert respuesta.json() == {
        "umbral_similitud": conf.umbral_similitud,
        "ventana_repetido_s": conf.ventana_repetido_s,
        "alerta_desconocidos": conf.alerta_desconocidos,
        "alerta_ventana_s": conf.alerta_ventana_s,
        "inscripcion_muestras": conf.inscripcion_muestras,
        "inscripcion_vence_s": conf.inscripcion_vence_s,
        "cara_min_px": conf.cara_min_px,
        "nitidez_min": conf.nitidez_min,
        "zona_horaria": conf.zona_horaria,
        "modelo_deteccion": "yunet_2023mar",
        "modelo_huella": "sface_2021dec",
        "version": __version__,
    }


@pytest.mark.marca("contrato API · verConfiguracion")
def test_los_valores_salen_del_entorno(sesion: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # D-14: las reglas se cambian en infra/.env y se reinicia el servidor; aquí basta leer otra vez la configuración.
    monkeypatch.setenv("UMBRAL_SIMILITUD", "0.4")
    monkeypatch.setenv("VENTANA_REPETIDO_S", "90")
    configuracion.cache_clear()
    try:
        cuerpo = sesion.get(CONFIGURACION).json()
    finally:
        monkeypatch.undo()
        configuracion.cache_clear()

    assert (cuerpo["umbral_similitud"], cuerpo["ventana_repetido_s"]) == (0.4, 90)


@pytest.mark.marca("contrato API · verConfiguracion")
def test_el_modelo_de_huella_es_el_que_guarda_la_base(sesion: TestClient, conexion: Connection) -> None:
    # rostro.modelo toma su valor por defecto del SQL del contrato: los dos nombres no pueden separarse.
    por_defecto = conexion.execute(
        text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = 'rostro' AND column_name = 'modelo'"
        )
    ).scalar_one()

    assert por_defecto == f"'{sesion.get(CONFIGURACION).json()['modelo_huella']}'::text"
