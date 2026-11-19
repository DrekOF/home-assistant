/**
 * Nombre: prueba_envio.cpp
 * Descripción: Pruebas del envío del recorte contra api-dispositivo.md 1.2: la URL, el puntaje y la espera tras cada respuesta.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include <initializer_list>
#include <optional>

#include "accesia/envio_logica.hpp"
#include "accesia/espera.hpp"

using accesia::espera_tras_envio;
using accesia::EsperaEntreRecortes;

TEST_CASE("contrato cámara · petición · la URL de enviarRostro")
{
    CHECK(accesia::url_rostros("http://192.168.137.250:8000", "entrada") ==
          "http://192.168.137.250:8000/api/v1/dispositivos/entrada/rostros");
    CHECK(accesia::url_rostros("http://192.168.137.250:8000/", "entrada-2") ==
          "http://192.168.137.250:8000/api/v1/dispositivos/entrada-2/rostros");
}

TEST_CASE("contrato cámara · petición · X-AccesIA-Puntaje va de 0 a 1")
{
    CHECK(accesia::texto_puntaje(0.934f) == "0.93");
    CHECK(accesia::texto_puntaje(1.0f) == "1.00");
    CHECK(accesia::texto_puntaje(1.4f) == "1.00");
    CHECK(accesia::texto_puntaje(-0.1f) == "0.00");
}

TEST_CASE("contrato cámara · 200 · espera 3 s tras una decisión y 1 s con lo demás")
{
    for (const char* resultado : {"permitido", "denegado", "desconocido"}) {
        CAPTURE(resultado);
        CHECK(espera_tras_envio(200, resultado, std::nullopt, 0) == 3000);
    }
    for (const char* resultado : {"descartado", "muestra_aceptada", "muestra_rechazada"}) {
        CAPTURE(resultado);
        CHECK(espera_tras_envio(200, resultado, std::nullopt, 0) == 1000);
    }
}

TEST_CASE("contrato cámara · 401 y 403 · reintenta cada 30 s")
{
    CHECK(espera_tras_envio(401, "", std::nullopt, 0) == 30'000);
    CHECK(espera_tras_envio(403, "", std::nullopt, 0) == 30'000);
}

TEST_CASE("contrato cámara · 429 · espera lo que diga Retry-After")
{
    CHECK(espera_tras_envio(429, "", 1, 0) == 1000);
    CHECK(espera_tras_envio(429, "", 4, 0) == 4000);
    CHECK(espera_tras_envio(429, "", std::nullopt, 0) == 1000);  // sin la cabecera, 1 s, el del servidor
    CHECK(accesia::leer_reintentar("1") == 1);
    CHECK(accesia::leer_reintentar(" 2 ") == 2);
    CHECK_FALSE(accesia::leer_reintentar("").has_value());
    CHECK_FALSE(accesia::leer_reintentar("0").has_value());
    CHECK_FALSE(accesia::leer_reintentar("Wed, 21 Oct 2026 07:28:00 GMT").has_value());
}

TEST_CASE("contrato cámara · sin respuesta o 5xx · reintenta con 1, 2, 4 y hasta 10 s")
{
    CHECK(accesia::TIEMPO_ESPERA_HTTP_MS == 5000);
    for (const int http : {accesia::SIN_RESPUESTA, 500, 502, 503}) {
        CAPTURE(http);
        CHECK(accesia::es_fallo(http));
        CHECK(espera_tras_envio(http, "", std::nullopt, 1) == 1000);
        CHECK(espera_tras_envio(http, "", std::nullopt, 2) == 2000);
        CHECK(espera_tras_envio(http, "", std::nullopt, 3) == 4000);
        CHECK(espera_tras_envio(http, "", std::nullopt, 4) == 8000);
        CHECK(espera_tras_envio(http, "", std::nullopt, 5) == 10'000);
        CHECK(espera_tras_envio(http, "", std::nullopt, 40) == 10'000);
    }
    CHECK_FALSE(accesia::es_fallo(200));
    CHECK_FALSE(accesia::es_fallo(429));
}

TEST_CASE("contrato cámara · 413, 415 y 422 · espera el mínimo de 1 s")
{
    for (const int http : {413, 415, 422, 404}) {
        CAPTURE(http);
        CHECK(espera_tras_envio(http, "", std::nullopt, 0) == accesia::ESPERA_MINIMA_MS);
    }
}

TEST_CASE("contrato cámara · la espera de un error se cuenta desde que termina el envío")
{
    EsperaEntreRecortes espera;
    espera.recorte_enviado();
    CHECK(espera.faltan_ms(100) == -1);
    espera.esperar_desde(5000, espera_tras_envio(accesia::SIN_RESPUESTA, "", std::nullopt, 1));
    CHECK_FALSE(espera.puede_enviar(5999));
    CHECK(espera.puede_enviar(6000));
}
