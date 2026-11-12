/**
 * Nombre: deteccion.cpp
 * Descripción: Corre HumanFaceDetect (MSRMNP_S8_V1) sobre el cuadro de la cámara y pasa sus cajas al formato (x, y, w, h).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/deteccion.hpp"

#include <cstdint>

#include "human_face_detect.hpp"

namespace accesia {

Detector::Detector() : modelo_(std::make_unique<HumanFaceDetect>(HumanFaceDetect::MSRMNP_S8_V1)) {}

Detector::~Detector() = default;

std::vector<CaraDetectada> Detector::detectar(const camera_fb_t& cuadro)
{
    dl::image::img_t imagen = {};
    imagen.data = cuadro.buf;
    imagen.width = static_cast<uint16_t>(cuadro.width);
    imagen.height = static_cast<uint16_t>(cuadro.height);
    imagen.pix_type = dl::image::DL_IMAGE_PIX_TYPE_RGB565BE;  // esp32-camera entrega el byte alto primero

    std::vector<CaraDetectada> caras;
    for (const dl::detect::result_t& resultado : modelo_->run(imagen)) {
        if (resultado.box.size() < 4) {
            continue;
        }
        // ESP-DL da las esquinas (x1, y1) y (x2, y2); el contrato usa esquina, ancho y alto.
        const int x1 = resultado.box[0];
        const int y1 = resultado.box[1];
        caras.push_back({Caja{x1, y1, resultado.box[2] - x1, resultado.box[3] - y1}, resultado.score});
    }
    return caras;
}

}  // namespace accesia
