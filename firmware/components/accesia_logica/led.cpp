/**
 * Nombre: led.cpp
 * Descripción: Patrones del LED de estado de la placa.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/led.hpp"

namespace accesia {

bool led_encendido(bool puerta_abierta, Conexion conexion, std::int64_t ahora_ms)
{
    if (puerta_abierta) {
        return true;
    }
    switch (conexion) {
    case Conexion::sin_wifi:
        return (ahora_ms / PARPADEO_SIN_WIFI_MS) % 2 == 0;
    case Conexion::sin_broker:
        return (ahora_ms / PARPADEO_SIN_BROKER_MS) % 2 == 0;
    case Conexion::conectada:
        break;
    }
    return false;
}

}  // namespace accesia
