/**
 * Nombre: prueba_placa.cpp
 * Descripción: Pruebas de la XIAO ESP32-C6: la antena (RF-14 · C2) y los GPIO que puede usar la puerta (RF-14 · C6).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include <initializer_list>
#include <string>

#include "accesia/placa_c6.hpp"

using accesia::Antena;

TEST_CASE("RF-14 · C2 · la antena es interna o externa")
{
    CHECK(accesia::leer_antena("interna") == Antena::interna);
    CHECK(accesia::leer_antena("externa") == Antena::externa);
    CHECK_FALSE(accesia::leer_antena("u.fl").has_value());
    CHECK(std::string(accesia::nombre_antena(Antena::externa)) == "externa");
}

TEST_CASE("RF-14 · C2 · pines de la placa según la wiki de Seeed")
{
    CHECK(accesia::PIN_DHT == 2);
    CHECK(accesia::PIN_CONMUTADOR == 3);
    CHECK(accesia::PIN_ANTENA == 14);
    CHECK(accesia::PIN_LED == 15);
}

TEST_CASE("RF-14 · C6 · la puerta puede usar el LED y los pines libres de la XIAO")
{
    std::string motivo;
    for (const int gpio : {0, 1, 15, 18, 19, 20, 21, 22, 23}) {
        CAPTURE(gpio);
        CHECK(accesia::gpio_utilizable_c6(gpio, motivo));
    }
}

TEST_CASE("RF-14 · C6 · la puerta no puede usar pines reservados")
{
    for (const int gpio : {2, 3, 14, 9, 12, 13, 16, 17, 24, 30, 31, -2}) {
        CAPTURE(gpio);
        std::string motivo;
        CHECK_FALSE(accesia::gpio_utilizable_c6(gpio, motivo));
        CHECK_FALSE(motivo.empty());
    }
}
