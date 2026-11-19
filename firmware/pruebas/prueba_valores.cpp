/**
 * Nombre: prueba_valores.cpp
 * Descripción: Pruebas de los valores de fábrica de la placa: el servidor y el broker apuntan a la IP fija de la Raspberry Pi (D-22), que está en un solo lugar.
 * Fecha de creación: 2026-11-18
 * Actualización: 2026-11-18
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include <string>

#include "accesia/valores_de_fabrica.hpp"

TEST_CASE("D-22 · el servidor y el broker de fábrica están en la IP de la Pi")
{
    const std::string ip = ACCESIA_IP_DE_LA_PI;
    CHECK(std::string(accesia::SERVIDOR_POR_DEFECTO) == "http://" + ip + ":8000");
    CHECK(std::string(accesia::MQTT_POR_DEFECTO) == "mqtt://" + ip + ":1883");
}

TEST_CASE("D-22 · la IP de la Pi está en el hotspot y no es la del portátil")
{
    const std::string ip = ACCESIA_IP_DE_LA_PI;
    CHECK(ip.rfind("192.168.137.", 0) == 0);  // la red del hotspot de Windows (D-21)
    CHECK(ip != "192.168.137.1");             // el portátil, que con D-22 solo es el plan B
}
