/**
 * Nombre: placa_esp32cam.cpp
 * Descripción: Revisa si un GPIO de la ESP32-CAM AI-Thinker sirve para la puerta (D-24).
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/placa_esp32cam.hpp"

#include <initializer_list>

namespace accesia {

bool gpio_utilizable_esp32cam(int gpio, std::string& motivo)
{
    if (gpio < 0 || gpio > 39 || gpio == 20 || gpio == 24 || (gpio >= 28 && gpio <= 31)) {
        motivo = "el ESP32 no tiene el GPIO " + std::to_string(gpio);
        return false;
    }
    if (gpio >= 6 && gpio <= 11) {
        motivo = "los GPIO 6 a 11 son de la flash";
        return false;
    }
    const PinesCamaraEsp32Cam& c = PINES_CAMARA_ESP32CAM;
    for (const int pin : {c.pwdn, c.xclk, c.siod, c.sioc, c.d0, c.d1, c.d2, c.d3, c.d4, c.d5, c.d6, c.d7, c.vsync,
                          c.href, c.pclk}) {
        if (gpio == pin) {
            motivo = "el GPIO " + std::to_string(gpio) + " es de la cámara";
            return false;
        }
    }
    if (gpio == PIN_UART0_TX || gpio == PIN_UART0_RX) {
        motivo = "los GPIO 1 y 3 son de UART0, que usa la consola";
        return false;
    }
    if (gpio == 16 || gpio == 17) {
        motivo = "los GPIO 16 y 17 son de la PSRAM";
        return false;
    }
    if (gpio >= 34) {
        motivo = "los GPIO 34 a 39 solo son entradas";
        return false;
    }
    if (gpio == 12) {
        motivo = "el GPIO 12 decide el voltaje de la flash al arrancar, y un relé ahí puede impedir que arranque";
        return false;
    }
    return true;
}

}  // namespace accesia
