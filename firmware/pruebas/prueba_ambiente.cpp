/**
 * Nombre: prueba_ambiente.cpp
 * Descripción: Pruebas del sensor de ambiente: qué publica en cada lectura, null tras 3 fallas y rangos de cada DHT (RF-14 · C3).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include <string>

#include "accesia/ambiente_logica.hpp"

using accesia::Ambiente;
using accesia::TipoSensor;

namespace {

const std::string NULOS = R"({"temperatura": null, "humedad": null})";

}  // namespace

TEST_CASE("RF-14 · C3 · cada 30 s, y null después de 3 fallas seguidas")
{
    CHECK(accesia::PERIODO_AMBIENTE_MS == 30000);
    CHECK(accesia::FALLAS_PARA_NULL == 3);
}

TEST_CASE("RF-14 · C3 · una lectura buena publica sus valores")
{
    Ambiente ambiente;
    const auto mensaje = ambiente.registrar(true, TipoSensor::dht22, 24.6, 58.0);
    REQUIRE(mensaje.has_value());
    CHECK(*mensaje == R"({"temperatura": 24.6, "humedad": 58.0})");
    REQUIRE(ambiente.ultima().has_value());
    CHECK(ambiente.ultima()->temperatura == doctest::Approx(24.6));
}

TEST_CASE("RF-14 · C3 · dos fallas no publican y la tercera publica null")
{
    Ambiente ambiente;
    CHECK_FALSE(ambiente.registrar(false, TipoSensor::dht22, 0, 0).has_value());
    CHECK_FALSE(ambiente.registrar(false, TipoSensor::dht22, 0, 0).has_value());
    const auto tercera = ambiente.registrar(false, TipoSensor::dht22, 0, 0);
    REQUIRE(tercera.has_value());
    CHECK(*tercera == NULOS);
    CHECK(ambiente.fallas_seguidas() == 3);
}

TEST_CASE("RF-14 · C3 · con más fallas sigue en null y una lectura buena vuelve a los valores")
{
    Ambiente ambiente;
    ambiente.registrar(true, TipoSensor::dht11, 22.0, 50.0);
    for (int i = 0; i < 3; ++i) {
        ambiente.registrar(false, TipoSensor::dht11, 0, 0);
    }
    const auto cuarta = ambiente.registrar(false, TipoSensor::dht11, 0, 0);
    REQUIRE(cuarta.has_value());
    CHECK(*cuarta == NULOS);

    const auto buena = ambiente.registrar(true, TipoSensor::dht11, 23.0, 51.0);
    REQUIRE(buena.has_value());
    CHECK(*buena == R"({"temperatura": 23.0, "humedad": 51.0})");
    CHECK(ambiente.fallas_seguidas() == 0);

    // Tras volver, una sola falla no publica.
    CHECK_FALSE(ambiente.registrar(false, TipoSensor::dht11, 0, 0).has_value());
}

TEST_CASE("RF-14 · C3 · una lectura fuera del rango del sensor cuenta como falla")
{
    CHECK(accesia::lectura_valida(TipoSensor::dht22, -40.0, 0.0));
    CHECK(accesia::lectura_valida(TipoSensor::dht22, 80.0, 100.0));
    CHECK_FALSE(accesia::lectura_valida(TipoSensor::dht22, 25.0, 1408.0));  // un DHT11 leído como DHT22
    CHECK(accesia::lectura_valida(TipoSensor::dht11, 0.0, 20.0));
    CHECK_FALSE(accesia::lectura_valida(TipoSensor::dht11, 51.0, 50.0));
    CHECK_FALSE(accesia::lectura_valida(TipoSensor::dht11, 25.0, 95.0));

    Ambiente ambiente;
    CHECK_FALSE(ambiente.registrar(true, TipoSensor::dht11, 60.0, 50.0).has_value());
    CHECK(ambiente.fallas_seguidas() == 1);
    CHECK_FALSE(ambiente.ultima().has_value());
}

TEST_CASE("RF-14 · C3 · el sensor es dht22 o dht11")
{
    CHECK(accesia::leer_tipo_sensor("dht22") == TipoSensor::dht22);
    CHECK(accesia::leer_tipo_sensor("dht11") == TipoSensor::dht11);
    CHECK_FALSE(accesia::leer_tipo_sensor("DHT22").has_value());
    CHECK(std::string(accesia::nombre_sensor(TipoSensor::dht22)) == "dht22");
    CHECK(std::string(accesia::nombre_sensor(TipoSensor::dht11)) == "dht11");
}
