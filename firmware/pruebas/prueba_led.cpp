/**
 * Nombre: prueba_led.cpp
 * Descripción: Pruebas del LED de la placa: la puerta manda y, si no, muestra la conexión (RF-14 · C5).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include <cstdint>
#include <initializer_list>

#include "accesia/led.hpp"

using accesia::Conexion;

TEST_CASE("RF-14 · C5 · con la puerta abierta el LED queda encendido")
{
    for (const Conexion conexion : {Conexion::sin_wifi, Conexion::sin_broker, Conexion::conectada}) {
        for (const std::int64_t ms : {0, 160, 510, 1999}) {
            CHECK(accesia::led_encendido(true, conexion, ms));
        }
    }
}

TEST_CASE("RF-14 · C5 · conectada y con la puerta cerrada, el LED queda apagado")
{
    for (const std::int64_t ms : {0, 160, 510, 1999}) {
        CHECK_FALSE(accesia::led_encendido(false, Conexion::conectada, ms));
    }
}

TEST_CASE("RF-14 · C5 · sin Wi-Fi parpadea lento y sin broker parpadea rápido")
{
    CHECK(accesia::led_encendido(false, Conexion::sin_wifi, 0));
    CHECK(accesia::led_encendido(false, Conexion::sin_wifi, 499));
    CHECK_FALSE(accesia::led_encendido(false, Conexion::sin_wifi, 500));
    CHECK(accesia::led_encendido(false, Conexion::sin_wifi, 1000));

    CHECK(accesia::led_encendido(false, Conexion::sin_broker, 0));
    CHECK_FALSE(accesia::led_encendido(false, Conexion::sin_broker, 150));
    CHECK(accesia::led_encendido(false, Conexion::sin_broker, 300));
}
