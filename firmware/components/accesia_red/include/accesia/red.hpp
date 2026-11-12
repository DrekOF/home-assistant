/**
 * Nombre: red.hpp
 * Descripción: Wi-Fi de la placa en modo estación, con reconexión sola (D-21: el hotspot del portátil en 2,4 GHz).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <optional>
#include <string>

#include "esp_err.h"

#include "accesia/config.hpp"

namespace accesia {

/// Enciende el Wi-Fi y se conecta a la red configurada. Si se cae, reintenta cada 1, 2, 4, 8 y hasta 10 s.
/// En el C6, la antena ya tiene que estar elegida (placa_elegir_antena) antes de llamar a esto.
esp_err_t red_iniciar(const Config& config);

bool red_conectada();

/// IP de la placa, o vacío sin conexión.
std::string red_ip();

/// Potencia de la señal del Wi-Fi en dBm, o vacío sin conexión.
std::optional<int> red_rssi();

}  // namespace accesia
