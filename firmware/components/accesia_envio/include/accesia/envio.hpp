/**
 * Nombre: envio.hpp
 * Descripción: Envío del JPEG del recorte al servidor (api-dispositivo.md 1.2, operación enviarRostro) y lo que importa de su respuesta.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>

#include "accesia/envio_logica.hpp"

namespace accesia {

/// Lo que la cámara necesita de una respuesta del servidor.
struct RespuestaEnvio {
    int http = SIN_RESPUESTA;         // el estado HTTP, o SIN_RESPUESTA si no llegó en 5 s o no se pudo conectar
    std::string resultado;            // con 200: permitido, denegado, desconocido, descartado o los de la inscripción
    std::string mensaje;              // con 200, el «mensaje»; con un error, su «detalle»
    std::string codigo_error;         // con un error, su «codigo», por ejemplo token_invalido
    std::optional<int> reintentar_s;  // con 429, la cabecera Retry-After
    std::string error_red;            // sin respuesta: el error de ESP-IDF
};

/// POST del JPEG a url con Authorization: Bearer token, Content-Type: image/jpeg, X-AccesIA-Firmware y
/// X-AccesIA-Puntaje. Espera la respuesta hasta 5 s. El JPEG no se guarda ni se copia: se envía desde memoria.
RespuestaEnvio envio_enviar(const std::string& url, const std::string& token, const std::string& firmware,
                            const std::uint8_t* jpeg, std::size_t bytes, float puntaje);

}  // namespace accesia
