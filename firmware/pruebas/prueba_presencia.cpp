/**
 * Nombre: prueba_presencia.cpp
 * Descripción: Pruebas de la presencia de la placa contra contratos/mqtt.md 1.6: el mensaje, su descubrimiento y cuándo cambia.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>
#include <nlohmann/json.hpp>

#include <optional>

#include "accesia/mensajes.hpp"
#include "accesia/presencia_logica.hpp"

using accesia::PresenciaLogica;
using nlohmann::json;

namespace {

/// El ejemplo «Presencia» de la cámara `entrada`, copiado de mqtt.md 1.6 («Entidades que publica la placa»).
json ejemplo_presencia()
{
    return json::parse(R"({
      "name": "Presencia",
      "unique_id": "accesia_entrada_presencia",
      "default_entity_id": "binary_sensor.accesia_entrada_presencia",
      "state_topic": "accesia/entrada/presencia",
      "value_template": "{{ 'ON' if value_json.presente else 'OFF' }}",
      "json_attributes_topic": "accesia/entrada/presencia",
      "device_class": "occupancy",
      "availability_topic": "accesia/entrada/disponible",
      "device": { "identifiers": ["accesia_entrada"] },
      "origin": { "name": "AccesIA firmware", "sw_version": "1.0.0" }
    })");
}

}  // namespace

TEST_CASE("contrato MQTT · presencia")
{
    // El ejemplo de mqtt.md 1.6, y sin nadie el puntaje va en null.
    CHECK(json::parse(accesia::mensaje_presencia(true, 0.93f)) == json::parse(R"({ "presente": true, "puntaje": 0.93 })"));
    CHECK(json::parse(accesia::mensaje_presencia(false, std::nullopt)) ==
          json::parse(R"({ "presente": false, "puntaje": null })"));
    CHECK(accesia::tema("entrada", "presencia") == "accesia/entrada/presencia");
}

TEST_CASE("contrato MQTT · presencia · el puntaje va de 0 a 1 con dos decimales, y en null sin nadie")
{
    CHECK(accesia::mensaje_presencia(true, 0.9349f) == R"({"presente": true, "puntaje": 0.93})");
    CHECK(accesia::mensaje_presencia(true, 1.7f) == R"({"presente": true, "puntaje": 1.00})");
    CHECK(accesia::mensaje_presencia(true, -0.2f) == R"({"presente": true, "puntaje": 0.00})");
    CHECK(accesia::mensaje_presencia(true, std::nullopt) == R"({"presente": true, "puntaje": null})");
    CHECK(accesia::mensaje_presencia(false, 0.8f) == R"({"presente": false, "puntaje": null})");
}

TEST_CASE("contrato MQTT · descubrimiento de la placa · presencia")
{
    CHECK(accesia::tema_descubrimiento_presencia("entrada") == "homeassistant/binary_sensor/entrada/presencia/config");
    CHECK(json::parse(accesia::mensaje_descubrimiento_presencia("entrada", "1.0.0")) == ejemplo_presencia());
}

TEST_CASE("contrato MQTT · descubrimiento de la placa · presencia con un código con guion")
{
    const json mensaje = json::parse(accesia::mensaje_descubrimiento_presencia("entrada-2", "0.3.0"));
    CHECK(mensaje.at("unique_id") == "accesia_entrada_2_presencia");
    CHECK(mensaje.at("default_entity_id") == "binary_sensor.accesia_entrada_2_presencia");
    CHECK(mensaje.at("state_topic") == "accesia/entrada-2/presencia");
    CHECK(mensaje.at("json_attributes_topic") == "accesia/entrada-2/presencia");
    CHECK(mensaje.at("availability_topic") == "accesia/entrada-2/disponible");
    CHECK(mensaje.at("device").at("identifiers") == json::array({"accesia_entrada-2"}));
    CHECK(mensaje.at("origin").at("sw_version") == "0.3.0");
}

TEST_CASE("D-24 · presencia · al encender no hay nadie")
{
    const PresenciaLogica presencia;
    CHECK_FALSE(presencia.presente());
    CHECK_FALSE(presencia.puntaje().has_value());
}

TEST_CASE("D-24 · presencia · pasa a presente con la primera cara y publica una sola vez")
{
    PresenciaLogica presencia;
    CHECK(presencia.cuadro(true, 0.91f, 1000));  // cambió: hay que publicar
    CHECK(presencia.presente());
    CHECK(*presencia.puntaje() == doctest::Approx(0.91));
    CHECK_FALSE(presencia.cuadro(true, 0.87f, 1400));  // sigue presente: no se publica otra vez
    CHECK(*presencia.puntaje() == doctest::Approx(0.87));  // el de la última cara, para publicar al reconectarse
}

TEST_CASE("D-24 · presencia · vuelve a no presente tras 5 s sin caras, no antes")
{
    CHECK(accesia::PRESENCIA_SOSTENER_MS == 5000);
    PresenciaLogica presencia;
    presencia.cuadro(true, 0.9f, 10'000);
    CHECK_FALSE(presencia.cuadro(false, 0.0f, 12'000));
    CHECK_FALSE(presencia.cuadro(false, 0.0f, 14'999));
    CHECK(presencia.presente());
    CHECK(presencia.cuadro(false, 0.0f, 15'000));  // 5 s desde la última cara: cambió
    CHECK_FALSE(presencia.presente());
    CHECK_FALSE(presencia.puntaje().has_value());
    CHECK_FALSE(presencia.cuadro(false, 0.0f, 20'000));  // sin nadie no vuelve a publicar
}

TEST_CASE("D-24 · presencia · una cara en medio vuelve a contar los 5 s")
{
    PresenciaLogica presencia;
    presencia.cuadro(true, 0.9f, 0);
    CHECK_FALSE(presencia.cuadro(false, 0.0f, 4000));
    CHECK_FALSE(presencia.cuadro(true, 0.8f, 4500));  // la cara volvió: sigue presente
    CHECK_FALSE(presencia.cuadro(false, 0.0f, 9000));  // 4,5 s desde la última cara
    CHECK(presencia.cuadro(false, 0.0f, 9500));
}

TEST_CASE("D-24 · presencia · tras irse, la siguiente cara vuelve a publicar")
{
    PresenciaLogica presencia(1000);
    CHECK(presencia.cuadro(true, 0.9f, 0));
    CHECK(presencia.cuadro(false, 0.0f, 1000));
    CHECK(presencia.cuadro(true, 0.95f, 1200));
    CHECK(*presencia.puntaje() == doctest::Approx(0.95));
}
