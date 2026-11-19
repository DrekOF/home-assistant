/**
 * Nombre: espera.hpp
 * Descripción: Espera entre recortes del contrato api-dispositivo.md: 1 s desde cada respuesta, 3 s tras una decisión y la de cada error (lógica pura).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

#pragma once

#include <cstdint>
#include <string_view>

namespace accesia {

/// Espera mínima desde que llega cualquier respuesta del servidor (RF-01 · C2).
inline constexpr std::int64_t ESPERA_MINIMA_MS = 1000;

/// Espera tras permitido, denegado o desconocido (api-dispositivo.md, «Qué hace la cámara con la respuesta»).
inline constexpr std::int64_t ESPERA_TRAS_DECISION_MS = 3000;

/// Milisegundos que la cámara espera, desde que recibe una respuesta con este resultado, antes del siguiente
/// recorte. La espera tras un error HTTP (401, 403, 429, sin respuesta y 5xx) la da espera_tras_envio
/// (envio_logica.hpp).
std::int64_t espera_tras(std::string_view resultado);

/// Cuándo se puede enviar el siguiente recorte. Los tiempos son milisegundos de un reloj que solo avanza.
class EsperaEntreRecortes {
public:
    /// Se envió un recorte: no se envía otro hasta tener su respuesta.
    void recorte_enviado();

    /// Llegó la respuesta con este resultado: la espera se cuenta desde ahora, no desde el envío.
    void respuesta_recibida(std::int64_t ahora_ms, std::string_view resultado);
    /// Terminó el envío, con respuesta o sin ella, y hay que esperar espera_ms desde ahora.
    void esperar_desde(std::int64_t ahora_ms, std::int64_t espera_ms);

    bool puede_enviar(std::int64_t ahora_ms) const;

    /// Milisegundos que faltan para poder enviar: 0 si ya se puede y -1 mientras se espera la respuesta.
    std::int64_t faltan_ms(std::int64_t ahora_ms) const;

private:
    bool esperando_respuesta_ = false;
    bool hay_espera_ = false;
    std::int64_t listo_desde_ms_ = 0;
};

}  // namespace accesia
