/**
 * Nombre: deteccion.hpp
 * Descripción: Detector de caras de la ESP32-CAM con ESP-DL 1.1, en dos etapas: MSR01 propone y MNP01 confirma (D-24, P-05).
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <memory>

#include "accesia/vision.hpp"

class HumanFaceDetectMSR01;
class HumanFaceDetectMNP01;

namespace accesia {

/// Caras de un cuadro RGB565 con MSR01 + MNP01, los umbrales del ejemplo human_face_detect de ESP-DL 1.1.
class DetectorEspDl final : public vision::Detector {
public:
    DetectorEspDl();
    ~DetectorEspDl() override;
    DetectorEspDl(const DetectorEspDl&) = delete;
    DetectorEspDl& operator=(const DetectorEspDl&) = delete;

    /// Las cajas van como (x, y, w, h) del contrato, con el puntaje de cada una; hay_alguien si quedó alguna.
    vision::Deteccion detectar(const vision::Cuadro& cuadro) override;

private:
    std::unique_ptr<HumanFaceDetectMSR01> msr_;
    std::unique_ptr<HumanFaceDetectMNP01> mnp_;
};

}  // namespace accesia
