/**
 * Nombre: envio_logica.cpp
 * Descripción: URL, puntaje y espera tras cada respuesta del envío del recorte (api-dispositivo.md 1.2).
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/envio_logica.hpp"

#include <cstdio>

#include "accesia/espera.hpp"

namespace accesia {

std::string url_rostros(std::string_view servidor, std::string_view codigo)
{
    while (!servidor.empty() && servidor.back() == '/') {
        servidor.remove_suffix(1);
    }
    std::string url(servidor);
    url += "/api/v1/dispositivos/";
    url += codigo;
    url += "/rostros";
    return url;
}

std::string texto_puntaje(float puntaje)
{
    const float acotado = puntaje < 0.0f ? 0.0f : (puntaje > 1.0f ? 1.0f : puntaje);
    char texto[16];
    std::snprintf(texto, sizeof(texto), "%.2f", static_cast<double>(acotado));
    return texto;
}

std::optional<int> leer_reintentar(std::string_view texto)
{
    while (!texto.empty() && texto.front() == ' ') {
        texto.remove_prefix(1);
    }
    while (!texto.empty() && texto.back() == ' ') {
        texto.remove_suffix(1);
    }
    if (texto.empty() || texto.size() > 4) {
        return std::nullopt;
    }
    int segundos = 0;
    for (const char c : texto) {
        if (c < '0' || c > '9') {
            return std::nullopt;
        }
        segundos = segundos * 10 + (c - '0');
    }
    if (segundos < 1 || segundos > 3600) {
        return std::nullopt;
    }
    return segundos;
}

bool es_fallo(int http)
{
    return http == SIN_RESPUESTA || (http >= 500 && http <= 599);
}

std::int64_t espera_tras_envio(int http, std::string_view resultado, std::optional<int> reintentar_s,
                               int fallos_seguidos)
{
    if (http == 200) {
        return espera_tras(resultado);
    }
    if (http == 401 || http == 403) {
        return ESPERA_TOKEN_MS;
    }
    if (http == 429) {
        return static_cast<std::int64_t>(reintentar_s.value_or(1)) * 1000;
    }
    if (es_fallo(http)) {
        // 1, 2, 4, 8 y luego 10 s: se duplica con cada fallo seguido, con tope.
        std::int64_t espera = ESPERA_MINIMA_MS;
        for (int i = 1; i < fallos_seguidos && espera < ESPERA_FALLOS_MAXIMA_MS; ++i) {
            espera *= 2;
        }
        return espera < ESPERA_FALLOS_MAXIMA_MS ? espera : ESPERA_FALLOS_MAXIMA_MS;
    }
    return ESPERA_MINIMA_MS;
}

}  // namespace accesia
