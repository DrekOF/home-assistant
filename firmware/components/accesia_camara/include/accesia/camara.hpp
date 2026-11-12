/**
 * Nombre: camara.hpp
 * Descripción: Cámara de la placa en QVGA y RGB565 según el perfil, y JPEG del recorte en memoria (api-dispositivo.md).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <cstddef>
#include <cstdint>

#include "esp_camera.h"
#include "esp_err.h"

#include "accesia/perfiles.hpp"
#include "accesia/recorte.hpp"

namespace accesia {

inline constexpr int ANCHO_CUADRO = 320;  // QVGA (arquitectura.md, «Comportamiento»)
inline constexpr int ALTO_CUADRO = 240;
inline constexpr int CALIDAD_JPEG = 80;                  // api-dispositivo.md
inline constexpr std::size_t JPEG_MAXIMO = 100 * 1024;  // api-dispositivo.md: máximo 100 KB

/// Inicia la cámara con los pines y la orientación del perfil, en QVGA y RGB565.
esp_err_t camara_iniciar(const Perfil& perfil, const PinesCamara& pines);

/// Cuadro de la cámara, o nullptr si no llegó. Se devuelve con camara_devolver.
camera_fb_t* camara_capturar();
void camara_devolver(camera_fb_t* cuadro);

/// JPEG de un recorte. Vive solo en memoria y se libera al destruirse: no se guarda en ninguna parte (RNF-01).
class JpegRecorte {
public:
    JpegRecorte() = default;
    ~JpegRecorte();
    JpegRecorte(const JpegRecorte&) = delete;
    JpegRecorte& operator=(const JpegRecorte&) = delete;
    JpegRecorte(JpegRecorte&& otro) noexcept;
    JpegRecorte& operator=(JpegRecorte&& otro) noexcept;

    const uint8_t* datos() const { return datos_; }
    std::size_t bytes() const { return bytes_; }

private:
    friend esp_err_t codificar_recorte(const camera_fb_t& cuadro, const Recorte& recorte, JpegRecorte& jpeg);
    void liberar();

    uint8_t* datos_ = nullptr;
    std::size_t bytes_ = 0;
};

/// Copia el recorte del cuadro (RGB565) y lo comprime en JPEG de calidad 80.
esp_err_t codificar_recorte(const camera_fb_t& cuadro, const Recorte& recorte, JpegRecorte& jpeg);

}  // namespace accesia
