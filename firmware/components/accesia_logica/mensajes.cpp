/**
 * Nombre: mensajes.cpp
 * Descripción: Arma los temas y los JSON de ambiente, estado y descubrimiento de la placa (contratos/mqtt.md 1.2).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Sin biblioteca de JSON: los textos se escapan aquí y los números van con printf en la configuración regional «C».
 */

#include "accesia/mensajes.hpp"

#include <cstdio>

namespace accesia {
namespace {

/// Texto JSON entre comillas, con sus caracteres especiales escapados.
std::string json_texto(const std::string& texto)
{
    std::string salida = "\"";
    for (const char c : texto) {
        switch (c) {
        case '"':
            salida += "\\\"";
            break;
        case '\\':
            salida += "\\\\";
            break;
        case '\n':
            salida += "\\n";
            break;
        case '\r':
            salida += "\\r";
            break;
        case '\t':
            salida += "\\t";
            break;
        default:
            if (static_cast<unsigned char>(c) < 0x20) {
                char escape[8];
                std::snprintf(escape, sizeof(escape), "\\u%04x", static_cast<unsigned>(static_cast<unsigned char>(c)));
                salida += escape;
            } else {
                salida += c;
            }
        }
    }
    return salida + "\"";
}

/// Número con un decimal: 24.6, 58.0, -3.5.
std::string un_decimal(double valor)
{
    char texto[32];
    std::snprintf(texto, sizeof(texto), "%.1f", valor);
    return texto;
}

const char* objeto(SensorAmbiente sensor)
{
    return sensor == SensorAmbiente::temperatura ? "temperatura" : "humedad";
}

}  // namespace

std::string tema(const std::string& codigo, const std::string& sufijo)
{
    return "accesia/" + codigo + "/" + sufijo;
}

std::string codigo_para_entidad(const std::string& codigo)
{
    std::string salida = codigo;
    for (char& c : salida) {
        if (c == '-') {
            c = '_';
        }
    }
    return salida;
}

std::string mensaje_ambiente(const std::optional<Lectura>& lectura)
{
    if (!lectura) {
        return "{\"temperatura\": null, \"humedad\": null}";
    }
    return "{\"temperatura\": " + un_decimal(lectura->temperatura) + ", \"humedad\": " + un_decimal(lectura->humedad) +
           "}";
}

std::string tema_descubrimiento(const std::string& codigo, SensorAmbiente sensor)
{
    return std::string("homeassistant/sensor/") + codigo + "/" + objeto(sensor) + "/config";
}

std::string mensaje_descubrimiento(const std::string& codigo, SensorAmbiente sensor, const std::string& version)
{
    const bool es_temperatura = sensor == SensorAmbiente::temperatura;
    const std::string entidad = "accesia_" + codigo_para_entidad(codigo) + "_" + objeto(sensor);

    std::string json = "{";
    json += "\"name\": " + json_texto(es_temperatura ? "Temperatura" : "Humedad");
    json += ", \"unique_id\": " + json_texto(entidad);
    json += ", \"default_entity_id\": " + json_texto("sensor." + entidad);
    json += ", \"state_topic\": " + json_texto(tema(codigo, "ambiente"));
    json += ", \"value_template\": " + json_texto(std::string("{{ value_json.") + objeto(sensor) + " }}");
    json += ", \"device_class\": " + json_texto(es_temperatura ? "temperature" : "humidity");
    json += ", \"unit_of_measurement\": " + json_texto(es_temperatura ? "°C" : "%");
    json += ", \"state_class\": \"measurement\"";
    json += ", \"suggested_display_precision\": 1";
    json += ", \"availability_topic\": " + json_texto(tema(codigo, "disponible"));
    json += ", \"device\": {\"identifiers\": [" + json_texto("accesia_" + codigo) + "]}";
    json += ", \"origin\": {\"name\": \"AccesIA firmware\", \"sw_version\": " + json_texto(version) + "}";
    json += "}";
    return json;
}

std::string mensaje_estado(const EstadoPlaca& estado)
{
    std::string json = "{";
    json += "\"perfil\": " + json_texto(estado.perfil);
    json += ", \"firmware\": " + json_texto(estado.firmware);
    json += ", \"ip\": " + (estado.ip.empty() ? std::string("null") : json_texto(estado.ip));
    json += ", \"rssi\": " + (estado.rssi ? std::to_string(*estado.rssi) : std::string("null"));
    json += ", \"libre_kb\": " + std::to_string(estado.libre_kb);
    if (!estado.sensor.empty()) {
        json += ", \"sensor\": " + json_texto(estado.sensor);
    }
    if (!estado.antena.empty()) {
        json += ", \"antena\": " + json_texto(estado.antena);
    }
    json += ", \"segundos_encendida\": " + std::to_string(estado.segundos_encendida);
    json += "}";
    return json;
}

}  // namespace accesia
