/**
 * Nombre: placa_c6.hpp
 * Descripción: Pines de la Seeed Studio XIAO ESP32-C6 (D-21, arquitectura.md), antena y GPIO que puede usar la puerta (lógica pura).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Pines de la wiki de Seeed (wiki.seeedstudio.com/xiao_esp32c6_getting_started), por verificar con la placa.
 */

#pragma once

#include <optional>
#include <string>
#include <string_view>

namespace accesia {

/// Perfil de la placa en EstadoCamara y en el texto del firmware.
inline constexpr const char* PERFIL_C6 = "xiao_esp32c6";

inline constexpr int PIN_DHT = 2;          // D2: DATA del DHT22 o DHT11
inline constexpr int PIN_CONMUTADOR = 3;   // en bajo enciende el conmutador de antena
inline constexpr int PIN_ANTENA = 14;      // en bajo la interna, en alto la externa U.FL
inline constexpr int PIN_LED = 15;         // LED de usuario; enciende en bajo

enum class Antena { interna, externa };

/// «interna» o «externa», como en el comando antena y en EstadoCamara.
const char* nombre_antena(Antena antena);

/// Lee «interna» o «externa». Otro texto, vacío.
std::optional<Antena> leer_antena(std::string_view texto);

/// true si el GPIO sirve para la puerta en la XIAO ESP32-C6. Si no, deja el motivo: no existe, es de la flash,
/// del USB o de UART0 (la consola), del sensor, de la antena o el botón BOOT. El LED (GPIO15) sí sirve.
bool gpio_utilizable_c6(int gpio, std::string& motivo);

}  // namespace accesia
