/**
 * Nombre: perfiles.cpp
 * Descripción: Los cinco perfiles de placa con la fuente oficial de cada pin, y la revisión de GPIO del ESP32-S3.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Todos los pines están por verificar con la placa: el hardware llega el día de la clase (P-02).
 */

#include "accesia/perfiles.hpp"

#include "sdkconfig.h"

namespace accesia {
namespace {

using CampoPin = int PinesCamara::*;

constexpr std::array<CampoPin, CANTIDAD_PINES> CAMPOS = {
    &PinesCamara::pwdn, &PinesCamara::reset, &PinesCamara::xclk, &PinesCamara::siod,
    &PinesCamara::sioc, &PinesCamara::d0,    &PinesCamara::d1,   &PinesCamara::d2,
    &PinesCamara::d3,   &PinesCamara::d4,    &PinesCamara::d5,   &PinesCamara::d6,
    &PinesCamara::d7,   &PinesCamara::vsync, &PinesCamara::href, &PinesCamara::pclk,
};

// ESP32-S3-EYE. Fuente: BSP oficial de Espressif, github.com/espressif/esp-bsp,
// bsp/esp32_s3_eye/include/bsp/esp32_s3_eye.h (BSP_CAMERA_GPIO_XCLK, BSP_CAMERA_D0 a D7, BSP_CAMERA_VSYNC,
// BSP_CAMERA_HSYNC, BSP_CAMERA_PCLK y el bus BSP_I2C_SDA/SCL). Sin PWDN ni RESET. BSP_CAMERA_VFLIP = 1.
// Freenove ESP32-S3 WROOM CAM usa los mismos pines. Fuente: github.com/Freenove/Freenove_ESP32_S3_WROOM_Board,
// C/Sketches/Sketch_07.1_CameraWebServer: board_config.h elige CAMERA_MODEL_ESP32S3_EYE y camera_pins.h
// trae esta tabla. Por verificar con la placa.
constexpr PinesCamara PINES_S3_EYE = {
    .pwdn = SIN_PIN,
    .reset = SIN_PIN,
    .xclk = 15,
    .siod = 4,
    .sioc = 5,
    .d0 = 11,
    .d1 = 9,
    .d2 = 8,
    .d3 = 10,
    .d4 = 12,
    .d5 = 18,
    .d6 = 17,
    .d7 = 16,
    .vsync = 6,
    .href = 7,
    .pclk = 13,
};

// Seeed Studio XIAO ESP32S3 Sense. Fuente: github.com/espressif/arduino-esp32,
// libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h (CAMERA_MODEL_XIAO_ESP32S3). Coincide con la
// tabla «Camera slot circuit design for expansion boards» de wiki.seeedstudio.com/xiao_esp32s3_camera_usage.
// La wiki no nombra PWDN ni RESET: quedan sin conectar, como en camera_pins.h. Por verificar con la placa.
constexpr PinesCamara PINES_XIAO_S3_SENSE = {
    .pwdn = SIN_PIN,
    .reset = SIN_PIN,
    .xclk = 10,
    .siod = 40,
    .sioc = 39,
    .d0 = 15,
    .d1 = 17,
    .d2 = 18,
    .d3 = 16,
    .d4 = 14,
    .d5 = 12,
    .d6 = 11,
    .d7 = 48,
    .vsync = 38,
    .href = 47,
    .pclk = 13,
};

// Orientación: el BSP del EYE voltea la imagen (VFLIP 1, HFLIP 0); el sketch de Freenove, con el sensor OV2640,
// la voltea y la refleja. Con otro sensor puede cambiar: se revisa con la placa.
const std::array<Perfil, 5> PERFILES = {{
    {"esp32s3_eye", "ESP32-S3-EYE (Espressif)", TipoPsram::octal, false, PINES_S3_EYE, true, false,
     "BSP de Espressif, esp-bsp: bsp/esp32_s3_eye/include/bsp/esp32_s3_eye.h"},
    {"freenove_s3_cam", "Freenove ESP32-S3 WROOM CAM", TipoPsram::octal, false, PINES_S3_EYE, true, true,
     "Freenove_ESP32_S3_WROOM_Board: Sketch_07.1_CameraWebServer (CAMERA_MODEL_ESP32S3_EYE)"},
    {"xiao_s3_sense", "Seeed Studio XIAO ESP32S3 Sense", TipoPsram::octal, false, PINES_XIAO_S3_SENSE, false, false,
     "arduino-esp32: CameraWebServer/camera_pins.h (CAMERA_MODEL_XIAO_ESP32S3) y wiki de Seeed"},
    {"generico_octal", "Otra ESP32-S3 con cámara y PSRAM octal", TipoPsram::octal, true, PinesCamara{}, false, false,
     "pines por consola (comando pin)"},
    {"generico_quad", "Otra ESP32-S3 con cámara y PSRAM quad", TipoPsram::quad, true, PinesCamara{}, false, false,
     "pines por consola (comando pin)"},
}};

}  // namespace

int valor_pin(const PinesCamara& pines, std::size_t i)
{
    return i < CANTIDAD_PINES ? pines.*CAMPOS[i] : SIN_PIN;
}

int* pin_por_nombre(PinesCamara& pines, std::string_view nombre)
{
    for (std::size_t i = 0; i < CANTIDAD_PINES; ++i) {
        if (nombre == NOMBRES_PINES[i]) {
            return &(pines.*CAMPOS[i]);
        }
    }
    return nullptr;
}

bool pin_opcional(std::string_view nombre)
{
    return nombre == "pwdn" || nombre == "reset";
}

const std::array<Perfil, 5>& perfiles()
{
    return PERFILES;
}

TipoPsram psram_del_binario()
{
#if CONFIG_SPIRAM_MODE_OCT
    return TipoPsram::octal;
#else
    return TipoPsram::quad;
#endif
}

const char* nombre_psram(TipoPsram psram)
{
    return psram == TipoPsram::octal ? "octal" : "quad";
}

const Perfil* buscar_perfil(std::string_view nombre)
{
    for (const Perfil& perfil : PERFILES) {
        if (perfil.psram == psram_del_binario() && nombre == perfil.nombre) {
            return &perfil;
        }
    }
    return nullptr;
}

bool gpio_utilizable(int gpio, std::string& motivo)
{
    if (gpio < 0 || gpio > 48 || (gpio >= 22 && gpio <= 25)) {
        motivo = "el ESP32-S3 no tiene el GPIO " + std::to_string(gpio);
        return false;
    }
    if (gpio >= 26 && gpio <= 32) {
        motivo = "los GPIO 26 a 32 son de la flash y la PSRAM";
        return false;
    }
    if (gpio >= 33 && gpio <= 37 && psram_del_binario() == TipoPsram::octal) {
        motivo = "los GPIO 33 a 37 son de la PSRAM octal";
        return false;
    }
    if (gpio == 19 || gpio == 20) {
        motivo = "los GPIO 19 y 20 son del USB nativo, que usa la consola";
        return false;
    }
    if (gpio == 43 || gpio == 44) {
        motivo = "los GPIO 43 y 44 son de UART0, que usa la consola";
        return false;
    }
    return true;
}

bool gpio_de_arranque(int gpio)
{
    return gpio == 0 || gpio == 3 || gpio == 45 || gpio == 46;
}

bool revisar_pines(const PinesCamara& pines, std::string& motivo)
{
    for (std::size_t i = 0; i < CANTIDAD_PINES; ++i) {
        const int gpio = valor_pin(pines, i);
        const char* nombre = NOMBRES_PINES[i];
        if (gpio == SIN_PIN) {
            if (pin_opcional(nombre)) {
                continue;
            }
            motivo = std::string("falta el pin ") + nombre;
            return false;
        }
        std::string porque;
        if (!gpio_utilizable(gpio, porque)) {
            motivo = std::string("el pin ") + nombre + " (GPIO " + std::to_string(gpio) + ") no sirve: " + porque;
            return false;
        }
        for (std::size_t j = 0; j < i; ++j) {
            if (valor_pin(pines, j) == gpio) {
                motivo = "el GPIO " + std::to_string(gpio) + " está en " + NOMBRES_PINES[j] + " y en " + nombre;
                return false;
            }
        }
    }
    return true;
}

}  // namespace accesia
