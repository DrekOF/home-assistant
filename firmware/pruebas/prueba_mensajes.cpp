/**
 * Nombre: prueba_mensajes.cpp
 * Descripción: Pruebas de los mensajes MQTT de la placa contra contratos/mqtt.md: ambiente, descubrimiento y estado (la presencia, en prueba_presencia.cpp).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

#include <doctest/doctest.h>
#include <nlohmann/json.hpp>

#include <optional>

#include "accesia/mensajes.hpp"

using accesia::SensorAmbiente;
using nlohmann::json;

namespace {

/// El ejemplo «Temperatura» de la cámara `entrada`, copiado de mqtt.md 1.2 («Entidades que publica la placa»).
json ejemplo_temperatura()
{
    return json::parse(R"({
      "name": "Temperatura",
      "unique_id": "accesia_entrada_temperatura",
      "default_entity_id": "sensor.accesia_entrada_temperatura",
      "state_topic": "accesia/entrada/ambiente",
      "value_template": "{{ value_json.temperatura }}",
      "device_class": "temperature",
      "unit_of_measurement": "°C",
      "state_class": "measurement",
      "suggested_display_precision": 1,
      "availability_topic": "accesia/entrada/disponible",
      "device": { "identifiers": ["accesia_entrada"] },
      "origin": { "name": "AccesIA firmware", "sw_version": "1.0.0" }
    })");
}

}  // namespace

TEST_CASE("contrato MQTT · ambiente")
{
    CHECK(json::parse(accesia::mensaje_ambiente(accesia::Lectura{24.6, 58.0})) ==
          json::parse(R"({ "temperatura": 24.6, "humedad": 58.0 })"));
    CHECK(json::parse(accesia::mensaje_ambiente(std::nullopt)) ==
          json::parse(R"({ "temperatura": null, "humedad": null })"));
}

TEST_CASE("contrato MQTT · ambiente · con un decimal")
{
    CHECK(accesia::mensaje_ambiente(accesia::Lectura{21.0, 47.0}) == R"({"temperatura": 21.0, "humedad": 47.0})");
    CHECK(accesia::mensaje_ambiente(accesia::Lectura{-3.54, 99.96}) == R"({"temperatura": -3.5, "humedad": 100.0})");
}

TEST_CASE("contrato MQTT · descubrimiento de la placa")
{
    CHECK(accesia::tema_descubrimiento("entrada", SensorAmbiente::temperatura) ==
          "homeassistant/sensor/entrada/temperatura/config");
    CHECK(json::parse(accesia::mensaje_descubrimiento("entrada", SensorAmbiente::temperatura, "1.0.0")) ==
          ejemplo_temperatura());

    // Humedad cambia en el nombre, la entidad, la plantilla, la clase y la unidad.
    json humedad = ejemplo_temperatura();
    humedad["name"] = "Humedad";
    humedad["unique_id"] = "accesia_entrada_humedad";
    humedad["default_entity_id"] = "sensor.accesia_entrada_humedad";
    humedad["value_template"] = "{{ value_json.humedad }}";
    humedad["device_class"] = "humidity";
    humedad["unit_of_measurement"] = "%";
    CHECK(accesia::tema_descubrimiento("entrada", SensorAmbiente::humedad) ==
          "homeassistant/sensor/entrada/humedad/config");
    CHECK(json::parse(accesia::mensaje_descubrimiento("entrada", SensorAmbiente::humedad, "1.0.0")) == humedad);
}

TEST_CASE("contrato MQTT · descubrimiento de la placa · código con guion")
{
    const json mensaje = json::parse(accesia::mensaje_descubrimiento("entrada-2", SensorAmbiente::humedad, "0.2.0"));
    CHECK(mensaje.at("unique_id") == "accesia_entrada_2_humedad");
    CHECK(mensaje.at("default_entity_id") == "sensor.accesia_entrada_2_humedad");
    CHECK(mensaje.at("state_topic") == "accesia/entrada-2/ambiente");
    CHECK(mensaje.at("availability_topic") == "accesia/entrada-2/disponible");
    CHECK(mensaje.at("device").at("identifiers") == json::array({"accesia_entrada-2"}));
    CHECK(mensaje.at("origin").at("sw_version") == "0.2.0");
    CHECK(accesia::tema_descubrimiento("entrada-2", SensorAmbiente::humedad) ==
          "homeassistant/sensor/entrada-2/humedad/config");
}

TEST_CASE("contrato MQTT · estado")
{
    accesia::EstadoPlaca estado;
    estado.perfil = "xiao_esp32c6";
    estado.firmware = "tinyml-xiao_esp32c6-1.0.0";
    estado.ip = "192.168.137.23";
    estado.rssi = -52;
    estado.libre_kb = 210;
    estado.sensor = "dht22";
    estado.antena = "interna";
    estado.segundos_encendida = 5321;

    // El ejemplo de la XIAO ESP32-C6 en mqtt.md 1.2: sin psram_kb.
    const json mensaje = json::parse(accesia::mensaje_estado(estado));
    CHECK(mensaje == json::parse(R"({ "perfil": "xiao_esp32c6", "firmware": "tinyml-xiao_esp32c6-1.0.0",
        "ip": "192.168.137.23", "rssi": -52, "libre_kb": 210, "sensor": "dht22", "antena": "interna",
        "segundos_encendida": 5321 })"));
    CHECK_FALSE(mensaje.contains("psram_kb"));
}

TEST_CASE("contrato MQTT · estado · ESP32-CAM, con psram_kb y sin sensor ni antena (D-24)")
{
    accesia::EstadoPlaca estado;
    estado.perfil = "esp32cam";
    estado.firmware = "tinyml-esp32cam-0.3.0";
    estado.ip = "192.168.137.31";
    estado.rssi = -61;
    estado.psram_kb = 4096;
    estado.libre_kb = 3900;
    estado.segundos_encendida = 120;

    // Los campos del ejemplo del ESP32-S3 de mqtt.md 1.6, que también tiene PSRAM.
    const json mensaje = json::parse(accesia::mensaje_estado(estado));
    CHECK(mensaje == json::parse(R"({ "perfil": "esp32cam", "firmware": "tinyml-esp32cam-0.3.0",
        "ip": "192.168.137.31", "rssi": -61, "psram_kb": 4096, "libre_kb": 3900, "segundos_encendida": 120 })"));
}

TEST_CASE("contrato MQTT · estado · sin IP ni RSSI van en null, y sin sensor ni antena no van")
{
    accesia::EstadoPlaca estado;
    estado.perfil = "xiao_esp32c6";
    estado.firmware = "tinyml-xiao_esp32c6-0.2.0";
    const json mensaje = json::parse(accesia::mensaje_estado(estado));
    CHECK(mensaje.at("ip").is_null());
    CHECK(mensaje.at("rssi").is_null());
    CHECK_FALSE(mensaje.contains("sensor"));
    CHECK_FALSE(mensaje.contains("antena"));
}

TEST_CASE("contrato MQTT · temas de la cámara y entidades")
{
    CHECK(accesia::tema("entrada", "ambiente") == "accesia/entrada/ambiente");
    CHECK(accesia::tema("entrada", "puerta/set") == "accesia/entrada/puerta/set");
    CHECK(accesia::codigo_para_entidad("punto-de-acceso-2") == "punto_de_acceso_2");
}

TEST_CASE("mensajes · los textos se escapan y el JSON sigue siendo válido")
{
    accesia::EstadoPlaca estado;
    estado.perfil = "xiao_esp32c6";
    estado.firmware = "version \"rara\"\\\n";
    const json mensaje = json::parse(accesia::mensaje_estado(estado));
    CHECK(mensaje.at("firmware") == "version \"rara\"\\\n");
}
