/**
 * Nombre: valores_de_fabrica.hpp
 * Descripción: La IP fija de la Raspberry Pi y las direcciones de fábrica del servidor y del broker (D-22), sin ESP-IDF, para que las pruebas de la lógica pura las comprueben.
 * Fecha de creación: 2026-11-18
 * Actualización: 2026-11-18
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Con D-22, la API y el broker de la demo están en la Pi. Si en clase la Pi queda en otra IP (P-04), se cambia
 * solo ACCESIA_IP_DE_LA_PI y se recompila. Sin recompilar, la placa se ajusta con los comandos servidor y mqtt de
 * la consola (RF-14 · C6).
 */

#pragma once

/// IP fija de la Raspberry Pi en el hotspot de Windows del portátil (D-22). Es una macro para armar con ella las
/// direcciones de abajo y los ejemplos de la consola sin repetirla.
#define ACCESIA_IP_DE_LA_PI "192.168.137.250"

namespace accesia {

/// La API del servidor, en el complemento accesia_servidor de la Pi.
inline constexpr const char* SERVIDOR_POR_DEFECTO = "http://" ACCESIA_IP_DE_LA_PI ":8000";
/// El broker, el Mosquitto oficial de la Pi.
inline constexpr const char* MQTT_POR_DEFECTO = "mqtt://" ACCESIA_IP_DE_LA_PI ":1883";

}  // namespace accesia
