/**
 * Nombre: esp32cam.hpp
 * Descripción: La ESP32-CAM AI-Thinker (D-24): arranca la cámara, el modelo y el ciclo de detección, presencia y envío, el LED rojo y sus comandos.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <string>

#include "esp_err.h"

#include "accesia/config.hpp"
#include "accesia/led.hpp"

namespace accesia {

/// Funciones que la placa le da a este componente. Las que falten no se usan.
struct EnlacesEsp32Cam {
    void (*publicar_presencia)(const std::string& mensaje) = nullptr;  // accesia/{codigo}/presencia, al cambiar
    bool (*puerta_abierta_en_led)() = nullptr;                          // el LED rojo muestra la puerta abierta
    Conexion (*conexion)() = nullptr;                                   // para el parpadeo del LED
    bool (*hay_red)() = nullptr;                                        // sin Wi-Fi no prepara recortes
};

/// Registra el comando «cara_min», las líneas de «estado» y el revisor de GPIO de la puerta, y arranca la tarea
/// del LED rojo (GPIO33). Después inicia la cámara y las dos tareas del ciclo: visión (cuadro, modelo, presencia y
/// recorte) y envío (HTTP). Si la cámara no arranca, lo dice y devuelve el error: la consola, la puerta y MQTT
/// siguen andando. Llamar después de consola_iniciar.
esp_err_t esp32cam_iniciar(const Config& config, const EnlacesEsp32Cam& enlaces);

/// El mensaje Presencia de ahora (mqtt.md 1.6), para publicarlo al conectarse al broker.
std::string esp32cam_mensaje_presencia();

/// KB de PSRAM de la placa (4096 en la AI-Thinker), para EstadoCamara; 0 si no arrancó la PSRAM.
int esp32cam_psram_kb();

}  // namespace accesia
