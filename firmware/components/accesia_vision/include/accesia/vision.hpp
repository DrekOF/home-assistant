/**
 * Nombre: vision.hpp
 * Descripción: Punto de extensión para la cámara que llega la próxima clase (D-21, P-03): fuente de cuadros y detector.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Solo interfaces, sin código de cámara ni de TinyML. Qué las implementa depende del módulo (arquitectura.md,
 * «Cuando llegue el módulo de cámara»):
 *   - Cámara SPI con JPEG en el C6: la fuente lee el JPEG por SPI; el detector es un clasificador int8 de
 *     TensorFlow Lite Micro (esp-tflite-micro) que dice si hay alguien, sin cajas. El envío del cuadro completo
 *     necesita antes un cambio de api-dispositivo.md y openapi.yaml, en su propio PR.
 *   - ESP32-S3 con cámara: vuelve el firmware del PR #7 (esp32-camera y HumanFaceDetect), con cajas y recorte.
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
};

/// El modelo TinyML que corre en la placa.
class Detector {
public:
    virtual ~Detector() = default;
    virtual Deteccion detectar(const Cuadro& cuadro) = 0;
};

}  // namespace accesia::vision
