/**
 * Nombre: config.hpp
 * Descripción: Configuración de la cámara guardada en NVS (arquitectura.md, «Configuración por consola serial»).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <string>

#include "esp_err.h"

#include "accesia/perfiles.hpp"

namespace accesia {

// Valores por defecto de arquitectura.md: la red propia de la Raspberry, el usuario MQTT de las cámaras,
// CARA_MIN_PX y los 3 s de la puerta.
inline constexpr const char* WIFI_POR_DEFECTO = "AccesIA";
inline constexpr const char* SERVIDOR_POR_DEFECTO = "http://10.42.0.1:8000";
inline constexpr const char* MQTT_POR_DEFECTO = "mqtt://10.42.0.1:1883";
inline constexpr const char* MQTT_USUARIO_POR_DEFECTO = "camara";
inline constexpr int CARA_MIN_POR_DEFECTO = 80;
inline constexpr int PUERTA_SEGUNDOS_POR_DEFECTO = 3;

struct Config {
    std::string perfil;  // vacío hasta el comando «perfil»: sin perfil, la cámara no se inicia
    std::string wifi_ssid = WIFI_POR_DEFECTO;
    std::string wifi_clave;
    std::string servidor = SERVIDOR_POR_DEFECTO;
    std::string codigo;
    std::string token;
    std::string mqtt_url = MQTT_POR_DEFECTO;
    std::string mqtt_usuario = MQTT_USUARIO_POR_DEFECTO;
    std::string mqtt_clave;
    PinesCamara pines;  // los de los perfiles genéricos
    int puerta_pin = SIN_PIN;
    int puerta_segundos = PUERTA_SEGUNDOS_POR_DEFECTO;
    int cara_min = CARA_MIN_POR_DEFECTO;
};

/// Inicia NVS y carga la configuración guardada. Lo que no esté guardado queda con su valor por defecto.
esp_err_t config_iniciar();

/// Copia de la configuración actual.
Config config_leer();

/// Guarda toda la configuración en NVS y la deja como la actual.
esp_err_t config_guardar(const Config& nueva);

/// Versión del firmware como la piden el contrato y MQTT: tinyml-<perfil>-<versión>.
std::string texto_firmware(const std::string& perfil);

}  // namespace accesia
