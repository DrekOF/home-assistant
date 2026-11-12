/**
 * Nombre: placa.hpp
 * Descripción: Lo propio de la XIAO ESP32-C6 (D-21): la antena, el LED de estado y qué GPIO puede usar la puerta.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include "esp_err.h"

#include "accesia/led.hpp"
#include "accesia/placa_c6.hpp"

namespace accesia {

/// Enciende el conmutador de antena (GPIO3 en bajo) y elige la antena guardada con GPIO14 (interna de fábrica).
/// Va antes del Wi-Fi: ESP-IDF no lo hace solo.
esp_err_t placa_elegir_antena();

/// Registra el comando «antena», la línea de «estado» y el revisor de GPIO de la puerta, y arranca la tarea del
/// LED de GPIO15. Llamar después de consola_iniciar.
esp_err_t placa_iniciar(bool (*puerta_abierta_en_led)(), Conexion (*conexion)());

Antena placa_antena();

}  // namespace accesia
