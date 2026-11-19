/**
 * Nombre: envio_logica.hpp
 * Descripción: Lógica pura del envío del recorte (api-dispositivo.md 1.2): la URL, el puntaje y la espera tras cada respuesta o error.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Sin ESP-IDF, para probarla en el PC. El envío por HTTP vive en accesia_envio.
 */

#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace accesia {

/// El http de un envío que no tuvo respuesta en el tiempo de espera (5 s) o no pudo conectarse.
inline constexpr int SIN_RESPUESTA = 0;
/// Tiempo de espera de la petición (api-dispositivo.md, «Qué hace la cámara con la respuesta»).
inline constexpr int TIEMPO_ESPERA_HTTP_MS = 5000;
/// Con 401 o 403, la cámara reintenta cada 30 s: el token se corrige por consola.
inline constexpr std::int64_t ESPERA_TOKEN_MS = 30000;
/// Tope de la espera creciente tras fallos seguidos (sin respuesta o 5xx): 1, 2, 4 y hasta 10 s.
inline constexpr std::int64_t ESPERA_FALLOS_MAXIMA_MS = 10000;

/// {servidor}/api/v1/dispositivos/{codigo}/rostros, sin barra doble si el servidor termina en «/».
std::string url_rostros(std::string_view servidor, std::string_view codigo);

/// El puntaje para X-AccesIA-Puntaje: de 0 a 1, con dos decimales («0.93»).
std::string texto_puntaje(float puntaje);

/// Segundos de la cabecera Retry-After. Vacío si no es un entero de 1 a 3600.
std::optional<int> leer_reintentar(std::string_view texto);

/// true si el envío cuenta como fallo para la espera creciente: sin respuesta o un 5xx.
bool es_fallo(int http);

/// Milisegundos que la cámara espera, desde que termina el envío, antes del siguiente recorte:
///   200: 3 s tras permitido, denegado o desconocido, y 1 s con lo demás (espera_tras);
///   401 o 403: 30 s;  429: lo que diga Retry-After, o 1 s;
///   sin respuesta o 5xx: 1, 2, 4, 8 y hasta 10 s, según fallos_seguidos (cuenta este y los anteriores seguidos);
///   cualquier otro (413, 415, 422…): 1 s, el mínimo.
std::int64_t espera_tras_envio(int http, std::string_view resultado, std::optional<int> reintentar_s,
                               int fallos_seguidos);

}  // namespace accesia
