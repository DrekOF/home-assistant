"""
Nombre: test_arranque.py
Descripción: Prueba del arranque real de la app con Mosquitto en un contenedor (RF-07 · C1): el ciclo de vida de main.py se conecta a MQTT con MQTT_URL, publica online, el descubrimiento y el resumen, y al apagarse publica offline.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import pytest
from fastapi.testclient import TestClient
from mqtt_de_prueba import url_del_servidor

from accesia.config import configuracion
from accesia.main import crear_app

DISPONIBLE = "accesia/servidor/disponible"


@pytest.mark.marca("RF-07 · C1")
def test_al_arrancar_el_servidor_aparecen_sus_entidades_y_al_apagarse_queda_offline(
    url_base: str, broker_mqtt, escucha, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MQTT_URL", url_del_servidor(broker_mqtt))
    configuracion.cache_clear()
    try:
        # Con el bloque with, TestClient corre el ciclo de vida: arranque y apagado, como Uvicorn.
        with TestClient(crear_app()) as cliente:
            escucha.esperar(DISPONIBLE, lambda mensaje: mensaje.carga == "online")
            escucha.esperar("homeassistant/sensor/accesia_servidor/asistentes_hoy/config")
            escucha.esperar("accesia/resumen")
            salud = cliente.get("/api/v1/salud").json()
            assert (salud["mqtt"], salud["estado"]) == ("ok", "ok")

        escucha.esperar(DISPONIBLE, lambda mensaje: mensaje.carga == "offline")
    finally:
        monkeypatch.delenv("MQTT_URL")
        configuracion.cache_clear()
