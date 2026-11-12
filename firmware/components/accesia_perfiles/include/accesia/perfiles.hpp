/**
 * Nombre: perfiles.hpp
 * Descripción: Perfiles de placa del firmware (arquitectura.md, D-17): pines de la cámara, PSRAM, orientación y fuente.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <string_view>

namespace accesia {

/// Señal sin conectar. Solo se admite en pwdn y reset.
inline constexpr int SIN_PIN = -1;

/// Tipo de PSRAM. Se fija al compilar: cada binario trae solo los perfiles de su tipo (D-17).
enum class TipoPsram { octal, quad };

/// Pines de la cámara con los nombres del comando «pin». d0 a d7 son Y2 a Y9 en las tablas de Arduino.
struct PinesCamara {
    int pwdn = SIN_PIN;
    int reset = SIN_PIN;
    int xclk = SIN_PIN;
    int siod = SIN_PIN;  // SDA del bus SCCB
    int sioc = SIN_PIN;  // SCL del bus SCCB
    int d0 = SIN_PIN;
    int d1 = SIN_PIN;
    int d2 = SIN_PIN;
    int d3 = SIN_PIN;
    int d4 = SIN_PIN;
    int d5 = SIN_PIN;
    int d6 = SIN_PIN;
    int d7 = SIN_PIN;
    int vsync = SIN_PIN;
    int href = SIN_PIN;
    int pclk = SIN_PIN;
};

inline constexpr std::size_t CANTIDAD_PINES = 16;

/// Nombres de los pines, en el orden de PinesCamara.
inline constexpr std::array<const char*, CANTIDAD_PINES> NOMBRES_PINES = {
    "pwdn", "reset", "xclk", "siod", "sioc", "d0", "d1", "d2",
    "d3",   "d4",    "d5",   "d6",   "d7",   "vsync", "href", "pclk",
};

/// Valor del pin en la posición i de NOMBRES_PINES.
int valor_pin(const PinesCamara& pines, std::size_t i);

/// Campo del pin con ese nombre, o nullptr si el nombre no existe.
int* pin_por_nombre(PinesCamara& pines, std::string_view nombre);

/// true si el pin puede quedar sin conectar: pwdn y reset.
bool pin_opcional(std::string_view nombre);

struct Perfil {
    const char* nombre;
    const char* placa;
    TipoPsram psram;
    bool generico;      // los pines se ajustan con el comando «pin»
    PinesCamara pines;  // los de la fuente oficial; vacíos en los genéricos
    bool voltear;       // volteo vertical del sensor (vflip)
    bool espejo;        // espejo horizontal (hmirror)
    const char* fuente;
};

/// Los cinco perfiles de arquitectura.md.
const std::array<Perfil, 5>& perfiles();

/// PSRAM de este binario, según su sdkconfig.
TipoPsram psram_del_binario();
const char* nombre_psram(TipoPsram psram);

/// Perfil de este binario con ese nombre; nullptr si no existe o si es del otro binario.
const Perfil* buscar_perfil(std::string_view nombre);

/// Revisa un GPIO para la cámara o la puerta en este binario. Si no sirve, deja el motivo.
bool gpio_utilizable(int gpio, std::string& motivo);

/// true en los pines de arranque del ESP32-S3 (0, 3, 45 y 46): sirven, pero su nivel al encender importa.
bool gpio_de_arranque(int gpio);

/// Revisa los pines de la cámara: los obligatorios definidos, todos utilizables y ninguno repetido.
bool revisar_pines(const PinesCamara& pines, std::string& motivo);

}  // namespace accesia
