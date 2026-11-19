/**
 * Nombre: config.hpp
 * Descripción: Configuración común de la placa en NVS (arquitectura.md, «Consola serial»), y claves propias de cada componente.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-18
 * Autor: Equipo AccesIA
 * Versión: 1.2
 *
 * Lo común a cualquier placa va en Config: Wi-Fi, servidor, código, token, MQTT y puerta. Lo propio de un
 * componente (el sensor o la antena del C6; el perfil y los pines del S3) lo guarda él con config_texto.
 */

#pragma once

#include <string>

#include "esp_err.h"
#include "sdkconfig.h"

#include "accesia/valores_de_fabrica.hpp"

namespace accesia {

/// Sin salida: no hay LED ni relé para la puerta.
inline constexpr int PIN_NINGUNO = -1;

// Valores de fábrica. La red es el hotspot de Windows del portátil (D-21); el servidor y el broker, los de la Pi
// (SERVIDOR_POR_DEFECTO y MQTT_POR_DEFECTO, en valores_de_fabrica.hpp, D-22); el usuario MQTT de las cámaras y
// los 3 s de la puerta, los de arquitectura.md y mqtt.md.
inline constexpr const char* WIFI_POR_DEFECTO = "AccesIA";
inline constexpr const char* MQTT_USUARIO_POR_DEFECTO = "camara";
inline constexpr int PUERTA_SEGUNDOS_POR_DEFECTO = 3;

#if CONFIG_IDF_TARGET_ESP32C6
// En la XIAO ESP32-C6 la puerta es el LED de usuario, en GPIO15, que enciende en bajo (D-21).
inline constexpr int PUERTA_PIN_POR_DEFECTO = 15;
inline constexpr bool PUERTA_ACTIVO_BAJO_POR_DEFECTO = true;
#else
inline constexpr int PUERTA_PIN_POR_DEFECTO = PIN_NINGUNO;
inline constexpr bool PUERTA_ACTIVO_BAJO_POR_DEFECTO = false;
#endif

struct Config {
    std::string wifi_ssid = WIFI_POR_DEFECTO;
    std::string wifi_clave;
    std::string servidor = SERVIDOR_POR_DEFECTO;
    std::string codigo;
    std::string token;
    std::string mqtt_url = MQTT_POR_DEFECTO;
    std::string mqtt_usuario = MQTT_USUARIO_POR_DEFECTO;
    std::string mqtt_clave;
    int puerta_pin = PUERTA_PIN_POR_DEFECTO;
    int puerta_segundos = PUERTA_SEGUNDOS_POR_DEFECTO;
    bool puerta_activo_bajo = PUERTA_ACTIVO_BAJO_POR_DEFECTO;  // el nivel que enciende la salida
};

/// Inicia NVS y carga la configuración guardada. Lo que no esté guardado queda con su valor de fábrica.
esp_err_t config_iniciar();

/// Copia de la configuración actual.
Config config_leer();

/// Guarda toda la configuración común en NVS y la deja como la actual.
esp_err_t config_guardar(const Config& nueva);

/// Texto guardado con esa clave por un componente, o el valor por defecto si no hay nada guardado.
std::string config_texto(const char* clave, const char* por_defecto);

/// Guarda el texto de un componente con esa clave (máximo 15 caracteres, la regla de NVS).
esp_err_t config_guardar_texto(const char* clave, const std::string& valor);

/// Versión del firmware como la piden api-dispositivo.md y mqtt.md: tinyml-<perfil>-<versión>.
std::string texto_firmware(const std::string& perfil);

/// Versión del programa (PROJECT_VER), por ejemplo 0.2.0.
std::string version_programa();

}  // namespace accesia
