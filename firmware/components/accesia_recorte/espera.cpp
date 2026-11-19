/**
 * Nombre: espera.cpp
 * Descripción: Espera entre recortes según el resultado de la respuesta del servidor o el error del envío (api-dispositivo.md).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

#include "accesia/espera.hpp"

namespace accesia {

std::int64_t espera_tras(std::string_view resultado)
{
    if (resultado == "permitido" || resultado == "denegado" || resultado == "desconocido") {
        return ESPERA_TRAS_DECISION_MS;
    }
    // descartado, muestra_aceptada, muestra_rechazada y cualquier otro: el mínimo.
    return ESPERA_MINIMA_MS;
}

void EsperaEntreRecortes::recorte_enviado()
{
    esperando_respuesta_ = true;
}

void EsperaEntreRecortes::respuesta_recibida(std::int64_t ahora_ms, std::string_view resultado)
{
    esperar_desde(ahora_ms, espera_tras(resultado));
}

void EsperaEntreRecortes::esperar_desde(std::int64_t ahora_ms, std::int64_t espera_ms)
{
    esperando_respuesta_ = false;
    hay_espera_ = true;
    listo_desde_ms_ = ahora_ms + espera_ms;
}

bool EsperaEntreRecortes::puede_enviar(std::int64_t ahora_ms) const
{
    return faltan_ms(ahora_ms) == 0;
}

std::int64_t EsperaEntreRecortes::faltan_ms(std::int64_t ahora_ms) const
{
    if (esperando_respuesta_) {
        return -1;
    }
    if (!hay_espera_ || ahora_ms >= listo_desde_ms_) {
        return 0;
    }
    return listo_desde_ms_ - ahora_ms;
}

}  // namespace accesia
