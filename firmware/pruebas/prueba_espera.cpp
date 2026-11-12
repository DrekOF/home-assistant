/**
 * Nombre: prueba_espera.cpp
 * Descripción: Pruebas de la espera entre recortes: 1 s desde la respuesta (RF-01 · C2) y 3 s tras una decisión (contrato cámara).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include <initializer_list>

#include "accesia/espera.hpp"

using accesia::EsperaEntreRecortes;

TEST_CASE("RF-01 · C2 · al encender se puede enviar el primer recorte")
{
    EsperaEntreRecortes espera;
    CHECK(espera.puede_enviar(0));
    CHECK(espera.faltan_ms(0) == 0);
}

TEST_CASE("RF-01 · C2 · no se envía otro recorte mientras se espera la respuesta")
{
    EsperaEntreRecortes espera;
    espera.recorte_enviado();
    CHECK_FALSE(espera.puede_enviar(60'000));
    CHECK(espera.faltan_ms(60'000) == -1);
}

TEST_CASE("RF-01 · C2 · espera 1 s contado desde que llega la respuesta, no desde el envío")
{
    EsperaEntreRecortes espera;
    espera.recorte_enviado();                      // se envía en t = 0
    espera.respuesta_recibida(700, "descartado");  // la respuesta llega en t = 700 ms
    CHECK_FALSE(espera.puede_enviar(1000));        // 1 s desde el envío no basta
    CHECK_FALSE(espera.puede_enviar(1699));
    CHECK(espera.faltan_ms(1699) == 1);
    CHECK(espera.puede_enviar(1700));  // 1 s desde la respuesta
}

TEST_CASE("RF-01 · C2 · espera 1 s tras descartado y tras las muestras de una inscripción")
{
    for (const char* resultado : {"descartado", "muestra_aceptada", "muestra_rechazada"}) {
        CAPTURE(resultado);
        CHECK(accesia::espera_tras(resultado) == 1000);
    }
}

TEST_CASE("contrato cámara · espera 3 s tras permitido, denegado o desconocido")
{
    for (const char* resultado : {"permitido", "denegado", "desconocido"}) {
        CAPTURE(resultado);
        CHECK(accesia::espera_tras(resultado) == 3000);

        EsperaEntreRecortes espera;
        espera.recorte_enviado();
        espera.respuesta_recibida(5000, resultado);
        CHECK(espera.faltan_ms(5000) == 3000);
        CHECK_FALSE(espera.puede_enviar(7999));
        CHECK(espera.puede_enviar(8000));
    }
}

TEST_CASE("RF-01 · C2 · un resultado que la cámara no conoce espera el mínimo")
{
    CHECK(accesia::espera_tras("otro_resultado") == accesia::ESPERA_MINIMA_MS);
}
