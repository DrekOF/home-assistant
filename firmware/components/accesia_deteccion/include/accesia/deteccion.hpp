/**
 * Nombre: deteccion.hpp
 * Descripción: Detección de caras en la placa con HumanFaceDetect de ESP-DL (MSR + MNP, int8; RF-01 · C1).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <memory>
#include <vector>

#include "esp_camera.h"

#include "accesia/recorte.hpp"

class HumanFaceDetect;

namespace accesia {

struct CaraDetectada {
    Caja caja;
    float puntaje = 0.0f;
};

/// Detector de caras de ESP-DL con el modelo human_face_detect_msrmnp_s8_v1. El modelo se carga en la primera detección.
class Detector {
public:
    Detector();
    ~Detector();
    Detector(const Detector&) = delete;
    Detector& operator=(const Detector&) = delete;

    /// Caras del cuadro (RGB565 de la cámara), en el orden de ESP-DL: de mayor a menor puntaje.
    std::vector<CaraDetectada> detectar(const camera_fb_t& cuadro);

private:
    std::unique_ptr<HumanFaceDetect> modelo_;
};

}  // namespace accesia
