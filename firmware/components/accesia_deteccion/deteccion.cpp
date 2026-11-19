/**
 * Nombre: deteccion.cpp
 * Descripción: Corre MSR01 y MNP01 de ESP-DL 1.1 sobre el cuadro de la cámara y pasa sus cajas al formato (x, y, w, h) del contrato.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * ESP-DL 1.1 recibe el RGB565 de esp32-camera tal cual (el byte alto primero), como el ejemplo CameraWebServer.
 */

#include "accesia/deteccion.hpp"

#include <cstdint>
#include <list>
#include <vector>

#include "human_face_detect_mnp01.hpp"
#include "human_face_detect_msr01.hpp"

namespace accesia {

DetectorEspDl::DetectorEspDl()
    // MSR01: umbral 0,1, NMS 0,5, hasta 10 candidatas, y la imagen a 0,2 de su tamaño para buscar.
    // MNP01: umbral 0,5, NMS 0,3, hasta 5 caras.
    : msr_(std::make_unique<HumanFaceDetectMSR01>(0.1F, 0.5F, 10, 0.2F)),
      mnp_(std::make_unique<HumanFaceDetectMNP01>(0.5F, 0.3F, 5))
{
}

DetectorEspDl::~DetectorEspDl() = default;

vision::Deteccion DetectorEspDl::detectar(const vision::Cuadro& cuadro)
{
    vision::Deteccion deteccion;
    if (cuadro.jpeg || cuadro.datos == nullptr) {
        return deteccion;
    }
    // ESP-DL solo lee el cuadro, pero sus funciones piden un puntero no constante.
    auto* pixeles = reinterpret_cast<std::uint16_t*>(const_cast<std::uint8_t*>(cuadro.datos));
    const std::vector<int> forma = {cuadro.alto, cuadro.ancho, 3};
    std::list<dl::detect::result_t>& candidatas = msr_->infer(pixeles, forma);
    std::list<dl::detect::result_t>& caras = mnp_->infer(pixeles, forma, candidatas);

    for (const dl::detect::result_t& cara : caras) {
        if (cara.box.size() < 4) {
            continue;
        }
        // ESP-DL da las esquinas (x1, y1) y (x2, y2); el contrato usa esquina, ancho y alto.
        const int x1 = cara.box[0];
        const int y1 = cara.box[1];
        deteccion.caras.push_back(Caja{x1, y1, cara.box[2] - x1, cara.box[3] - y1});
        deteccion.puntajes.push_back(cara.score);
        if (cara.score > deteccion.puntaje) {
            deteccion.puntaje = cara.score;
        }
    }
    deteccion.hay_alguien = !deteccion.caras.empty();
    return deteccion;
}

}  // namespace accesia
