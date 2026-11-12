/**
 * Nombre: mensajes.hpp
 * Descripción: Temas y mensajes MQTT de la placa según contratos/mqtt.md 1.2: ambiente, estado y descubrimiento (lógica pura).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <optional>
#include <string>

namespace accesia {

/// Tema de la cámara: accesia/{codigo}/{sufijo}. Por ejemplo, tema("entrada", "ambiente").
std::string tema(const std::string& codigo, const std::string& sufijo);

/// El código como va en unique_id y default_entity_id: los guiones pasan a guion bajo (mqtt.md, «Broker»).
std::string codigo_para_entidad(const std::string& codigo);

/// Lectura válida del sensor de ambiente.
struct Lectura {
    double temperatura = 0.0;  // °C
    double humedad = 0.0;      // % de humedad relativa
};

/// Mensaje Ambiente: {"temperatura": 24.6, "humedad": 58.0}, con un decimal, o los dos en null sin lectura.
std::string mensaje_ambiente(const std::optional<Lectura>& lectura);

/// Los dos sensores de ambiente cuyo descubrimiento publica la placa.
enum class SensorAmbiente { temperatura, humedad };

/// Tema del descubrimiento de un sensor de la placa: homeassistant/sensor/{codigo}/{objeto}/config.
std::string tema_descubrimiento(const std::string& codigo, SensorAmbiente sensor);

/// JSON de descubrimiento de un sensor de la placa, como el ejemplo de mqtt.md («Entidades que publica la placa»).
std::string mensaje_descubrimiento(const std::string& codigo, SensorAmbiente sensor, const std::string& version);

/// Datos del mensaje EstadoCamara de la placa. No lleva psram_kb: la XIAO ESP32-C6 no tiene PSRAM.
struct EstadoPlaca {
    std::string perfil;
    std::string firmware;
    std::string ip;           // vacío si todavía no tiene IP: el campo va en null
    std::optional<int> rssi;  // sin Wi-Fi: null
    int libre_kb = 0;
    std::string sensor;  // dht22 o dht11; vacío si la placa no tiene sensor, y el campo no va
    std::string antena;  // interna o externa; vacío si la placa no elige antena, y el campo no va
    long long segundos_encendida = 0;
};

/// Mensaje EstadoCamara (mqtt.md, «Mensajes»).
std::string mensaje_estado(const EstadoPlaca& estado);

}  // namespace accesia
