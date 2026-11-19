/**
 * Nombre: prueba_esp32cam.cpp
 * Descripción: Pruebas de la ESP32-CAM AI-Thinker (D-24): los pines de la cámara y los GPIO que puede usar la puerta.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include <initializer_list>
#include <set>
#include <string>

#include "accesia/placa_esp32cam.hpp"

TEST_CASE("D-24 · pines · la cámara usa los de la AI-Thinker, sin repetir ninguno")
{
    const accesia::PinesCamaraEsp32Cam& c = accesia::PINES_CAMARA_ESP32CAM;
    CHECK(c.pwdn == 32);
    CHECK(c.reset == -1);
    CHECK(c.xclk == 0);
    CHECK(c.siod == 26);
    CHECK(c.sioc == 27);
    CHECK(c.vsync == 25);
    CHECK(c.href == 23);
    CHECK(c.pclk == 22);
    // D0 a D7 (Y2 a Y9 en Arduino).
    CHECK(c.d0 == 5);
    CHECK(c.d1 == 18);
    CHECK(c.d2 == 19);
    CHECK(c.d3 == 21);
    CHECK(c.d4 == 36);
    CHECK(c.d5 == 39);
    CHECK(c.d6 == 34);
    CHECK(c.d7 == 35);

    const std::set<int> usados = {c.pwdn, c.xclk, c.siod, c.sioc, c.d0, c.d1, c.d2, c.d3,
                                  c.d4,   c.d5,   c.d6,   c.d7,   c.vsync, c.href, c.pclk};
    CHECK(usados.size() == 15);
    CHECK(usados.count(accesia::PIN_LED_ROJO) == 0);
}

TEST_CASE("D-24 · pines · la puerta puede usar el LED rojo y los GPIO libres del conector")
{
    for (const int gpio : {33, 2, 4, 13, 14, 15}) {
        CAPTURE(gpio);
        std::string motivo;
        CHECK(accesia::gpio_utilizable_esp32cam(gpio, motivo));
        CHECK(motivo.empty());
    }
    CHECK(accesia::PIN_LED_ROJO == 33);
}

TEST_CASE("D-24 · pines · la puerta no puede usar los de la cámara, la consola, la PSRAM ni la flash")
{
    struct Caso {
        int gpio;
        const char* motivo;
    };
    for (const Caso caso : {Caso{0, "el GPIO 0 es de la cámara"}, Caso{32, "el GPIO 32 es de la cámara"},
                            Caso{26, "el GPIO 26 es de la cámara"}, Caso{35, "el GPIO 35 es de la cámara"},
                            Caso{1, "los GPIO 1 y 3 son de UART0, que usa la consola"},
                            Caso{3, "los GPIO 1 y 3 son de UART0, que usa la consola"},
                            Caso{16, "los GPIO 16 y 17 son de la PSRAM"}, Caso{8, "los GPIO 6 a 11 son de la flash"},
                            Caso{37, "los GPIO 34 a 39 solo son entradas"}, Caso{20, "el ESP32 no tiene el GPIO 20"},
                            Caso{40, "el ESP32 no tiene el GPIO 40"}, Caso{-1, "el ESP32 no tiene el GPIO -1"}}) {
        CAPTURE(caso.gpio);
        std::string motivo;
        CHECK_FALSE(accesia::gpio_utilizable_esp32cam(caso.gpio, motivo));
        CHECK(motivo == caso.motivo);
    }
    std::string motivo;
    CHECK_FALSE(accesia::gpio_utilizable_esp32cam(12, motivo));
    CHECK(motivo.find("voltaje de la flash") != std::string::npos);
}
