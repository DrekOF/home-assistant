/**
 * Nombre: camara.hpp
 * Descripción: La cámara de la ESP32-CAM (D-24): cuadros QVGA en RGB565 con esp32-camera y el JPEG del recorte en memoria.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Ninguna imagen se guarda: el cuadro vuelve a la cámara y el JPEG del recorte se libera al enviarse (RNF-01).
 */

#pragma once

#include <cstddef>
#include <cstdint>

#include "esp_err.h"

#include "accesia/recorte.hpp"
#include "accesia/vision.hpp"

namespace accesia {

inline constexpr int ANCHO_CUADRO = 320;  // QVGA (arquitectura.md, «Cámara»)
inline constexpr int ALTO_CUADRO = 240;
inline constexpr int CALIDAD_JPEG = 80;                 // api-dispositivo.md
inline constexpr std::size_t JPEG_MAXIMO = 102400;      // api-dispositivo.md: máximo 100 KB

/// Inicia la OV2640 con los pines de la AI-Thinker, en QVGA y RGB565, con dos cuadros en la PSRAM. Apaga el LED
/// del flash (GPIO4).
esp_err_t camara_iniciar();

/// PID del sensor (0x26 en la OV2640), o 0 si la cámara no arrancó.
int camara_sensor_pid();

/// La cámara como fuente de cuadros: toma uno a la vez y lo devuelve antes de tomar el siguiente.
class CamaraEsp32Cam final : public vision::FuenteDeCuadros {
public:
    bool capturar(vision::Cuadro& cuadro) override;
    void devolver(vision::Cuadro& cuadro) override;

private:
    void* actual_ = nullptr;  // el camera_fb_t del cuadro prestado
};

/// JPEG de un recorte, en la PSRAM. Se libera al destruirse, salvo que se suelte para enviarlo.
class JpegRecorte {
public:
    JpegRecorte() = default;
    ~JpegRecorte();
    JpegRecorte(const JpegRecorte&) = delete;
    JpegRecorte& operator=(const JpegRecorte&) = delete;

    const std::uint8_t* datos() const { return datos_; }
    std::size_t bytes() const { return bytes_; }
    /// Entrega los datos a quien los envía, que los libera con free.
    std::uint8_t* soltar();

private:
    friend esp_err_t codificar_recorte(const vision::Cuadro& cuadro, const Recorte& recorte, JpegRecorte& jpeg);
    std::uint8_t* datos_ = nullptr;
    std::size_t bytes_ = 0;
};

/// Copia el recorte del cuadro (RGB565) y lo comprime en JPEG de calidad 80.
esp_err_t codificar_recorte(const vision::Cuadro& cuadro, const Recorte& recorte, JpegRecorte& jpeg);

}  // namespace accesia
