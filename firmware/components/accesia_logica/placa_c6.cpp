/**
 * Nombre: placa_c6.cpp
 * Descripción: Antena y revisión de los GPIO de la XIAO ESP32-C6 para la puerta.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/placa_c6.hpp"

namespace accesia {

const char* nombre_antena(Antena antena)
{
    return antena == Antena::interna ? "interna" : "externa";
}

std::optional<Antena> leer_antena(std::string_view texto)
{
    if (texto == "interna") {
        return Antena::interna;
    }
    if (texto == "externa") {
        return Antena::externa;
    }
    return std::nullopt;
}

bool gpio_utilizable_c6(int gpio, std::string& motivo)
{
    if (gpio < 0 || gpio > 30) {
        motivo = "el ESP32-C6 no tiene el GPIO " + std::to_string(gpio);
        return false;
    }
    if (gpio >= 24) {
        motivo = "los GPIO 24 a 30 son de la flash";
        return false;
    }
    if (gpio == 12 || gpio == 13) {
        motivo = "los GPIO 12 y 13 son del USB, que usa la consola";
        return false;
    }
    if (gpio == 16 || gpio == 17) {
        motivo = "los GPIO 16 y 17 son de UART0, que usa la consola";
        return false;
    }
    if (gpio == PIN_DHT) {
        motivo = "el GPIO 2 es del sensor de temperatura y humedad";
        return false;
    }
    if (gpio == PIN_CONMUTADOR || gpio == PIN_ANTENA) {
        motivo = "los GPIO 3 y 14 son de la antena";
        return false;
    }
    if (gpio == 9) {
        motivo = "el GPIO 9 es el botón BOOT";
        return false;
    }
    return true;
}

}  // namespace accesia
