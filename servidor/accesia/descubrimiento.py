"""
Nombre: descubrimiento.py
Descripción: Descubrimiento de Home Assistant que publica el servidor (mqtt.md 1.3, Entidades): los seis config de cada cámara y los cuatro del servidor, y cómo reconocer en un tema un config del servidor para la limpieza de las cámaras que ya no existen.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import re

FABRICANTE = "Equipo AccesIA"
# D-21: la placa de la demo. Va en todas las cámaras, también en las de tipo simulador: en la demo, entrada se crea
# como simulador porque es quien envía los recortes, pero su dispositivo en Home Assistant es la placa, con su puerta
# y sus sensores (decisión de B2 del Día 3).
MODELO = "XIAO ESP32-C6"
ORIGEN = "AccesIA servidor"
DISPONIBLE_SERVIDOR = "accesia/servidor/disponible"
NODO_SERVIDOR = "accesia_servidor"
PREFIJO_NODO = "accesia_"

_CODIGO = re.compile(r"^[a-z0-9-]{3,32}$")

Config = tuple[str, dict]  # (tema, mensaje)


def tema_config(componente: str, nodo: str, objeto: str) -> str:
    return f"homeassistant/{componente}/{nodo}/{objeto}/config"


def para_entidad(codigo: str) -> str:
    """El código como va en unique_id y default_entity_id: los guiones pasan a guion bajo (mqtt.md, Broker)."""
    return codigo.replace("-", "_")


def _comun(dispositivo: dict, version: str) -> dict:
    return {"device": dispositivo, "origin": {"name": ORIGEN, "sw_version": version}}


def configs_de_camara(codigo: str, nombre: str, version: str) -> list[Config]:
    """Las seis entidades de la cámara, en el dispositivo «AccesIA {nombre}».

    identifiers y el nodo del tema llevan el código tal cual, como los config de la placa (accesia_entrada-2), para que
    Home Assistant junte las entidades del servidor y los sensores de la placa en un solo dispositivo.
    """
    entidad = para_entidad(codigo)
    nodo = PREFIJO_NODO + codigo
    disponible_camara = f"accesia/{codigo}/disponible"
    evento = f"accesia/{codigo}/evento"
    dispositivo = {
        "identifiers": [PREFIJO_NODO + codigo],
        "name": f"AccesIA {nombre}",
        "manufacturer": FABRICANTE,
        "model": MODELO,
        "sw_version": version,
    }
    comun = _comun(dispositivo, version)

    def ids(componente: str, objeto: str) -> dict:
        unico = f"accesia_{entidad}_{objeto}"
        return {"unique_id": unico, "default_entity_id": f"{componente}.{unico}"}

    return [
        (
            tema_config("sensor", nodo, "ultima_persona"),
            {
                "name": "Última persona",
                **ids("sensor", "ultima_persona"),
                "state_topic": evento,
                "value_template": "{{ value_json.persona.nombre if value_json.persona else 'Desconocido' }}",
                "json_attributes_topic": evento,
                "icon": "mdi:account-badge",
                "availability_topic": DISPONIBLE_SERVIDOR,
                **comun,
            },
        ),
        (
            tema_config("sensor", nodo, "ultimo_resultado"),
            {
                "name": "Último resultado",
                **ids("sensor", "ultimo_resultado"),
                "state_topic": evento,
                "value_template": "{{ value_json.resultado }}",
                "availability_topic": DISPONIBLE_SERVIDOR,
                **comun,
            },
        ),
        (
            tema_config("binary_sensor", nodo, "desconocido"),
            {
                "name": "Desconocido detectado",
                **ids("binary_sensor", "desconocido"),
                "state_topic": f"accesia/{codigo}/alerta",
                "value_template": "{{ 'ON' }}",
                "off_delay": 60,
                "device_class": "problem",
                "availability_topic": DISPONIBLE_SERVIDOR,
                **comun,
            },
        ),
        (
            tema_config("binary_sensor", nodo, "puerta"),
            {
                "name": "Puerta",
                **ids("binary_sensor", "puerta"),
                "state_topic": f"accesia/{codigo}/puerta/estado",
                "payload_on": "abierta",
                "payload_off": "cerrada",
                "device_class": "door",
                "availability_topic": disponible_camara,
                **comun,
            },
        ),
        (
            tema_config("button", nodo, "abrir_puerta"),
            {
                "name": "Abrir puerta",
                **ids("button", "abrir_puerta"),
                "command_topic": f"accesia/{codigo}/puerta/set",
                "payload_press": "ABRIR",
                "availability_topic": disponible_camara,
                **comun,
            },
        ),
        (
            tema_config("binary_sensor", nodo, "en_linea"),
            {
                "name": "Cámara en línea",
                **ids("binary_sensor", "en_linea"),
                "state_topic": disponible_camara,
                "payload_on": "online",
                "payload_off": "offline",
                "device_class": "connectivity",
                **comun,
            },
        ),
    ]


def configs_del_servidor(version: str) -> list[Config]:
    """Las cuatro entidades del dispositivo «AccesIA Servidor». Los sensores del resumen dependen de la
    disponibilidad del servidor, como las entidades de las cámaras que salen de él; «Servidor en línea» no."""
    dispositivo = {
        "identifiers": [NODO_SERVIDOR],
        "name": "AccesIA Servidor",
        "manufacturer": FABRICANTE,
        "sw_version": version,
    }
    comun = _comun(dispositivo, version)

    def sensor(objeto: str, nombre: str, campo: str) -> Config:
        return (
            tema_config("sensor", NODO_SERVIDOR, objeto),
            {
                "name": nombre,
                "unique_id": f"accesia_{objeto}",
                "default_entity_id": f"sensor.accesia_{objeto}",
                "state_topic": "accesia/resumen",
                "value_template": "{{ value_json." + campo + " }}",
                "unit_of_measurement": "personas",
                "state_class": "measurement",
                "availability_topic": DISPONIBLE_SERVIDOR,
                **comun,
            },
        )

    return [
        sensor("asistentes_hoy", "Asistentes hoy", "asistentes"),
        sensor("tarde_hoy", "Llegadas tarde hoy", "tarde"),
        sensor("desconocidos_hoy", "Desconocidos hoy", "desconocidos_hoy"),
        (
            tema_config("binary_sensor", NODO_SERVIDOR, "en_linea"),
            {
                "name": "Servidor en línea",
                "unique_id": "accesia_servidor_en_linea",
                "default_entity_id": "binary_sensor.accesia_servidor_en_linea",
                "state_topic": DISPONIBLE_SERVIDOR,
                "payload_on": "online",
                "payload_off": "offline",
                "device_class": "connectivity",
                **comun,
            },
        ),
    ]


def codigo_de_config(tema: str) -> str | None:
    """El código de la cámara de un config que publicó el servidor, o None si no es de una cámara del servidor.

    Son del servidor los de nodo accesia_{codigo}. Los de la placa usan el código como nodo y, como un código no lleva
    guion bajo, nunca empiezan por accesia_. Los del dispositivo del servidor (accesia_servidor) no son de una cámara.
    """
    partes = tema.split("/")
    if len(partes) != 5 or partes[0] != "homeassistant" or partes[4] != "config":
        return None
    nodo = partes[2]
    if not nodo.startswith(PREFIJO_NODO) or nodo == NODO_SERVIDOR:
        return None
    codigo = nodo.removeprefix(PREFIJO_NODO)
    return codigo if _CODIGO.match(codigo) else None
