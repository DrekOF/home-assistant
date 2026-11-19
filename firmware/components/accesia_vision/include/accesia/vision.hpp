/**
 * Nombre: vision.hpp
 * Descripción: Interfaces de la cámara de la placa: la fuente de cuadros y el detector (D-24).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.1
 *
 * En la ESP32-CAM (D-24, P-05) las implementan accesia_camara (esp32-camera, QVGA en RGB565) y accesia_deteccion
 * (ESP-DL 1.1, MSR01 + MNP01), con cajas y recorte, y accesia_esp32cam las usa en su ciclo. Si vuelve el ESP32-S3
 * del PR #7, sus HumanFaceDetect de ESP-DL 3 serían otra implementación del detector.
 * El ciclo de envío usa la espera de accesia_recorte (1 s, o 3 s tras una decisión).
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "accesia/recorte.hpp"

namespace accesia::vision {

/// Un cuadro de la cámara. Vive solo en memoria y se devuelve a su fuente: no se guarda (RNF-01).
struct Cuadro {
    const std::uint8_t* datos = nullptr;
    std::size_t bytes = 0;
    std::uint16_t ancho = 0;
    std::uint16_t alto = 0;
    bool jpeg = false;  // true si los datos ya son JPEG; si no, son píxeles
};

/// De dónde salen los cuadros: una cámara SPI o la cámara de la placa.
class FuenteDeCuadros {
public:
    virtual ~FuenteDeCuadros() = default;
    /// Toma un cuadro. Devuelve false si la cámara no entregó ninguno.
    virtual bool capturar(Cuadro& cuadro) = 0;
    /// Devuelve el cuadro para que la fuente lo reuse o lo libere.
    virtual void devolver(Cuadro& cuadro) = 0;
};

/// Lo que dice el detector sobre un cuadro.
struct Deteccion {
    bool hay_alguien = false;
    float puntaje = 0.0f;
    std::vector<Caja> caras;  // vacío si el detector no da cajas (por ejemplo, un clasificador)
    std::vector<float> puntajes;  // uno por cara, en el mismo orden de caras
};

/// El modelo TinyML que corre en la placa.
class Detector {
public:
    virtual ~Detector() = default;
    virtual Deteccion detectar(const Cuadro& cuadro) = 0;
};

}  // namespace accesia::vision
