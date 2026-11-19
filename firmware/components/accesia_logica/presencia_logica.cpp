/**
 * Nombre: presencia_logica.cpp
 * Descripción: Presencia de la placa en el tiempo (contratos/mqtt.md 1.6): cambia con la primera cara y tras 5 s sin caras.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/presencia_logica.hpp"

namespace accesia {

PresenciaLogica::PresenciaLogica(std::int64_t sostener_ms) : sostener_ms_(sostener_ms) {}

bool PresenciaLogica::cuadro(bool hay_alguien, float puntaje, std::int64_t ahora_ms)
{
    if (hay_alguien) {
        ultima_cara_ms_ = ahora_ms;
        puntaje_ = puntaje;
        if (!presente_) {
            presente_ = true;
            return true;
        }
        return false;
    }
    if (presente_ && ahora_ms - ultima_cara_ms_ >= sostener_ms_) {
        presente_ = false;
        return true;
    }
    return false;
}

std::optional<float> PresenciaLogica::puntaje() const
{
    if (!presente_) {
        return std::nullopt;
    }
    return puntaje_;
}

}  // namespace accesia
