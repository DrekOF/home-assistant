/**
 * Nombre: presencia_logica.hpp
 * Descripción: Cuándo cambia la presencia que publica la placa (contratos/mqtt.md 1.6): sí con la primera cara y no tras 5 s sin caras.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * mqtt.md 1.6 deja al firmware decidir cuándo vuelve a false, para que no parpadee, y que lo anote en
 * firmware/README.md. Lógica pura, sin ESP-IDF, para probarla en el PC.
 */

#pragma once

#include <cstdint>
#include <optional>

namespace accesia {

/// Tiempo sin caras para pasar a «no hay nadie». Cubre los cuadros en que la cara gira o el modelo no la ve.
inline constexpr std::int64_t PRESENCIA_SOSTENER_MS = 5000;

/// La presencia en el tiempo. Los tiempos son milisegundos de un reloj que solo avanza.
class PresenciaLogica {
public:
    explicit PresenciaLogica(std::int64_t sostener_ms = PRESENCIA_SOSTENER_MS);

    /// Resultado del modelo en un cuadro, con el puntaje de su mejor cara. Devuelve true si cambió presente, y
    /// entonces hay que publicarlo. Con alguien, pasa a presente en ese mismo cuadro; sin nadie, solo cuando se
    /// cumplen los milisegundos de sostener desde la última cara.
    bool cuadro(bool hay_alguien, float puntaje, std::int64_t ahora_ms);

    bool presente() const { return presente_; }

    /// Puntaje de la última cara mientras hay alguien; vacío sin nadie (mqtt.md 1.6: null).
    std::optional<float> puntaje() const;

private:
    std::int64_t sostener_ms_;
    bool presente_ = false;
    float puntaje_ = 0.0f;
    std::int64_t ultima_cara_ms_ = 0;
};

}  // namespace accesia
