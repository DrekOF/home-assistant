/**
 * Nombre: placa_esp32cam.hpp
 * Descripción: Perfil y pines de la ESP32-CAM AI-Thinker (D-24): la cámara OV2640, el LED rojo de la puerta y los GPIO que sirven para ella.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Lógica pura, sin ESP-IDF, para probarla en el PC. Los pines de la cámara son los del perfil AI-Thinker de
 * esp32-camera (CAMERA_MODEL_AI_THINKER), los mismos de arquitectura.md («Placa de la demo: ESP32-CAM»).
 */

#pragma once

#include <string>

namespace accesia {

/// Perfil de la placa en EstadoCamara y en el texto del firmware (tinyml-esp32cam-<versión>).
inline constexpr const char* PERFIL_ESP32CAM = "esp32cam";

/// Pines de la cámara. d0 a d7 son Y2 a Y9 en las tablas de Arduino; -1 si la señal no está conectada.
struct PinesCamaraEsp32Cam {
    int pwdn;
    int reset;
    int xclk;
    int siod;  // SDA del bus SCCB
    int sioc;  // SCL del bus SCCB
    int d0;
    int d1;
    int d2;
    int d3;
    int d4;
    int d5;
    int d6;
    int d7;
    int vsync;
    int href;
    int pclk;
};

/// La OV2640 de la AI-Thinker. XCLK sale por GPIO0, el mismo pin que a GND pone la placa en modo de descarga.
inline constexpr PinesCamaraEsp32Cam PINES_CAMARA_ESP32CAM = {
    32, -1, 0, 26, 27, 5, 18, 19, 21, 36, 39, 34, 35, 25, 23, 22,
};

inline constexpr int PIN_LED_ROJO = 33;   // LED rojo junto al módulo; enciende en bajo. Es la puerta de fábrica
inline constexpr int PIN_LED_FLASH = 4;   // LED blanco del flash; el firmware lo deja apagado
inline constexpr int PIN_UART0_TX = 1;    // U0T, al RX del adaptador USB
inline constexpr int PIN_UART0_RX = 3;    // U0R, al TX del adaptador USB

/// true si el GPIO sirve para la puerta en la ESP32-CAM. Si no, deja el motivo: no existe, es de la flash, de la
/// cámara, de UART0 (la consola), de la PSRAM, solo es entrada o decide el voltaje de la flash al arrancar.
/// Sirven 2, 4, 13, 14, 15 y 33 (el LED rojo).
bool gpio_utilizable_esp32cam(int gpio, std::string& motivo);

}  // namespace accesia
