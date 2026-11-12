/**
 * Nombre: prueba_puerta.cpp
 * Descripción: Pruebas de la puerta de la placa: ABRIR, CERRAR, el cierre por tiempo y el nivel de la salida (RF-14 · C5 y C6).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>

#include "accesia/puerta_logica.hpp"

using accesia::OrdenPuerta;
using accesia::PuertaLogica;

TEST_CASE("RF-14 · C5 · ABRIR abre y la puerta se cierra sola a los segundos configurados")
{
    PuertaLogica puerta(3);
    CHECK(puerta.orden(OrdenPuerta::abrir, 1000));  // cambió: se publica «abierta»
    CHECK(puerta.abierta());
    CHECK(puerta.cierra_en_ms() == 4000);
    CHECK_FALSE(puerta.actualizar(3999));
    CHECK(puerta.actualizar(4000));  // cambió: se publica «cerrada»
    CHECK_FALSE(puerta.abierta());
    CHECK(puerta.cierra_en_ms() == -1);
    CHECK_FALSE(puerta.actualizar(9000));  // ya cerrada: no publica otra vez
}

TEST_CASE("RF-14 · C5 · CERRAR la cierra antes")
{
    PuertaLogica puerta(3);
    puerta.orden(OrdenPuerta::abrir, 0);
    CHECK(puerta.orden(OrdenPuerta::cerrar, 1200));
    CHECK_FALSE(puerta.abierta());
    CHECK_FALSE(puerta.actualizar(3000));
    CHECK_FALSE(puerta.orden(OrdenPuerta::cerrar, 3500));  // cerrada: nada que publicar
}

TEST_CASE("RF-14 · C5 · ABRIR con la puerta abierta vuelve a contar los segundos sin publicar")
{
    PuertaLogica puerta(3);
    puerta.orden(OrdenPuerta::abrir, 0);
    CHECK_FALSE(puerta.orden(OrdenPuerta::abrir, 2000));  // una repetición de R4 la vuelve a abrir
    CHECK(puerta.cierra_en_ms() == 5000);
    CHECK_FALSE(puerta.actualizar(3000));
    CHECK(puerta.actualizar(5000));
}

TEST_CASE("RF-14 · C5 · solo ABRIR y CERRAR son órdenes")
{
    CHECK(accesia::leer_orden("ABRIR") == OrdenPuerta::abrir);
    CHECK(accesia::leer_orden("CERRAR") == OrdenPuerta::cerrar);
    CHECK(accesia::leer_orden("abrir") == OrdenPuerta::desconocida);
    CHECK(accesia::leer_orden("") == OrdenPuerta::desconocida);

    PuertaLogica puerta(3);
    CHECK_FALSE(puerta.orden(OrdenPuerta::desconocida, 0));
    CHECK_FALSE(puerta.abierta());
}

TEST_CASE("RF-14 · C6 · el nivel de la puerta es bajo o alto")
{
    CHECK(accesia::leer_activo_bajo("bajo") == true);
    CHECK(accesia::leer_activo_bajo("alto") == false);
    CHECK_FALSE(accesia::leer_activo_bajo("medio").has_value());
}
