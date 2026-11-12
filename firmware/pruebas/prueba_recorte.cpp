/**
 * Nombre: prueba_recorte.cpp
 * Descripción: Pruebas del recorte: casos de casos-recorte.json (contrato recorte), cara_min (RF-01 · C3) y bordes del cuadro.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include <doctest/doctest.h>
#include <nlohmann/json.hpp>

#include <cstddef>
#include <fstream>
#include <string>
#include <vector>

#include "accesia/recorte.hpp"

using accesia::Caja;
using nlohmann::json;

namespace {

constexpr int ANCHO = 320;
constexpr int ALTO = 240;

json leer_casos()
{
    std::ifstream archivo(CASOS_RECORTE);
    REQUIRE_MESSAGE(archivo.good(), "No se pudo abrir " CASOS_RECORTE);
    return json::parse(archivo);
}

std::vector<Caja> caras_del_caso(const json& caso)
{
    std::vector<Caja> caras;
    for (const json& cara : caso.at("caras")) {
        caras.push_back(Caja{cara.at("x").get<int>(), cara.at("y").get<int>(), cara.at("w").get<int>(),
                             cara.at("h").get<int>()});
    }
    return caras;
}

/// true si la elección coincide con el «esperado» del caso: la cara, las cuatro esquinas y el tamaño.
bool coincide(const accesia::Eleccion& eleccion, const json& esperado)
{
    const accesia::Recorte& r = eleccion.recorte;
    return eleccion.indice == esperado.at("cara").get<std::size_t>() && r.x0 == esperado.at("x0").get<int>() &&
           r.y0 == esperado.at("y0").get<int>() && r.x1 == esperado.at("x1").get<int>() &&
           r.y1 == esperado.at("y1").get<int>() && r.ancho() == esperado.at("ancho").get<int>() &&
           r.alto() == esperado.at("alto").get<int>();
}

}  // namespace

TEST_CASE("contrato recorte · casos de specs/contratos/casos-recorte.json")
{
    const json datos = leer_casos();
    CHECK(datos.at("margen").get<double>() == doctest::Approx(0.25));

    const json& casos = datos.at("casos");
    REQUIRE(casos.size() >= 2);

    // Cada caso se revisa aunque falle otro; si falla, el mensaje lleva su marca y lo obtenido.
    for (const json& caso : casos) {
        const std::string marca = "contrato recorte · " + caso.at("nombre").get<std::string>();
        INFO(marca);

        // cara_min 0: estos casos prueban la elección y la fórmula, no el tamaño mínimo.
        const auto eleccion = accesia::elegir_recorte(caras_del_caso(caso), caso.at("cuadro").at("ancho").get<int>(),
                                                      caso.at("cuadro").at("alto").get<int>(), 0);
        CHECK(eleccion.has_value());
        if (!eleccion) {
            continue;
        }
        const accesia::Recorte& r = eleccion->recorte;
        INFO("obtenido: cara " << eleccion->indice << ", de (" << r.x0 << ", " << r.y0 << ") a (" << r.x1 << ", "
                               << r.y1 << "), " << r.ancho() << " × " << r.alto());
        const bool bien = coincide(*eleccion, caso.at("esperado"));
        CHECK(bien);
        if (bien) {
            MESSAGE(marca << ": bien");
        }
    }
}

TEST_CASE("RF-01 · C3 · sin caras no se envía nada")
{
    CHECK_FALSE(accesia::elegir_recorte({}, ANCHO, ALTO, 80).has_value());
}

TEST_CASE("RF-01 · C3 · nada si la cara mide menos de cara_min de alto")
{
    const std::vector<Caja> baja{{100, 80, 70, 79}};
    CHECK_FALSE(accesia::elegir_recorte(baja, ANCHO, ALTO, 80).has_value());

    const std::vector<Caja> justa{{100, 80, 70, 80}};
    const auto eleccion = accesia::elegir_recorte(justa, ANCHO, ALTO, 80);
    REQUIRE(eleccion.has_value());
    CHECK(eleccion->indice == 0);
}

TEST_CASE("RF-01 · C3 · decide la cara de mayor área aunque otra sea más alta")
{
    // La de mayor área mide 60 px de alto: no se envía nada, aunque la otra mida 90 px.
    const std::vector<Caja> caras{{10, 10, 200, 60}, {250, 100, 50, 90}};
    CHECK_FALSE(accesia::elegir_recorte(caras, ANCHO, ALTO, 80).has_value());
}

TEST_CASE("recorte · con empate de área gana la primera, la de mayor puntaje")
{
    const std::vector<Caja> caras{{20, 20, 90, 100}, {180, 40, 100, 90}};
    const auto indice = accesia::cara_mayor(caras);
    REQUIRE(indice.has_value());
    CHECK(*indice == 0);
}

TEST_CASE("recorte · las cajas sin ancho o sin alto no cuentan")
{
    const std::vector<Caja> caras{{0, 0, 0, 120}, {10, 10, 300, -5}, {50, 40, 90, 100}};
    const auto indice = accesia::cara_mayor(caras);
    REQUIRE(indice.has_value());
    CHECK(*indice == 2);

    const std::vector<Caja> vacias{{5, 5, 0, 0}};
    CHECK_FALSE(accesia::cara_mayor(vacias).has_value());
}

TEST_CASE("recorte · el margen se corta en los cuatro bordes del cuadro")
{
    const accesia::Recorte recorte = accesia::calcular_recorte({20, 15, 280, 210}, ANCHO, ALTO);
    CHECK(recorte.x0 == 0);
    CHECK(recorte.y0 == 0);
    CHECK(recorte.x1 == ANCHO);
    CHECK(recorte.y1 == ALTO);
}

TEST_CASE("recorte · piso y techo exactos con márgenes fraccionarios")
{
    // w = 81: w/4 = 20,25, así que x0 = piso(79,75) = 79 y x1 = techo(201,25) = 202.
    // h = 83: h/4 = 20,75, así que y0 = piso(29,25) = 29 y y1 = techo(153,75) = 154.
    const accesia::Recorte recorte = accesia::calcular_recorte({100, 50, 81, 83}, ANCHO, ALTO);
    CHECK(recorte.x0 == 79);
    CHECK(recorte.y0 == 29);
    CHECK(recorte.x1 == 202);
    CHECK(recorte.y1 == 154);
    CHECK(recorte.ancho() == 123);
    CHECK(recorte.alto() == 125);
}

TEST_CASE("recorte · una caja que se sale del cuadro se recorta en el borde")
{
    const accesia::Recorte recorte = accesia::calcular_recorte({-10, 200, 60, 70}, ANCHO, ALTO);
    CHECK(recorte.x0 == 0);
    CHECK(recorte.x1 == 65);
    CHECK(recorte.y0 == 182);
    CHECK(recorte.y1 == ALTO);
}
