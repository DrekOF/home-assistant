/**
 * Nombre: recorte.cpp
 * Descripción: Elección de la cara de mayor área y fórmula del recorte con aritmética entera (api-dispositivo.md).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/recorte.hpp"

#include <algorithm>
#include <cstdint>

namespace accesia {
namespace {

/// División entera hacia abajo (piso) con divisor positivo, también para numeradores negativos.
std::int64_t dividir_piso(std::int64_t numerador, std::int64_t divisor)
{
    std::int64_t cociente = numerador / divisor;
    if (numerador % divisor != 0 && numerador < 0) {
        --cociente;
    }
    return cociente;
}

/// División entera hacia arriba (techo) con divisor positivo.
std::int64_t dividir_techo(std::int64_t numerador, std::int64_t divisor)
{
    return -dividir_piso(-numerador, divisor);
}

std::int64_t area(const Caja& caja)
{
    return static_cast<std::int64_t>(caja.w) * caja.h;
}

}  // namespace

std::optional<std::size_t> cara_mayor(const std::vector<Caja>& caras)
{
    std::optional<std::size_t> elegida;
    std::int64_t mayor = 0;
    for (std::size_t i = 0; i < caras.size(); ++i) {
        const Caja& caja = caras[i];
        if (caja.w <= 0 || caja.h <= 0) {
            continue;
        }
        // Solo una mayor estricta reemplaza: con empate se queda la primera.
        if (!elegida || area(caja) > mayor) {
            elegida = i;
            mayor = area(caja);
        }
    }
    return elegida;
}

Recorte calcular_recorte(const Caja& cara, int ancho_cuadro, int alto_cuadro)
{
    // Sin punto flotante: x - w/4 = (4x - w)/4 y x + w + w/4 = (4x + 5w)/4.
    const std::int64_t x = cara.x;
    const std::int64_t y = cara.y;
    const std::int64_t w = cara.w;
    const std::int64_t h = cara.h;

    Recorte recorte;
    recorte.x0 = static_cast<int>(std::max<std::int64_t>(0, dividir_piso(4 * x - w, 4)));
    recorte.y0 = static_cast<int>(std::max<std::int64_t>(0, dividir_piso(4 * y - h, 4)));
    recorte.x1 = static_cast<int>(std::min<std::int64_t>(ancho_cuadro, dividir_techo(4 * x + 5 * w, 4)));
    recorte.y1 = static_cast<int>(std::min<std::int64_t>(alto_cuadro, dividir_techo(4 * y + 5 * h, 4)));
    return recorte;
}

std::optional<Eleccion> elegir_recorte(const std::vector<Caja>& caras, int ancho_cuadro, int alto_cuadro,
                                       int cara_min)
{
    const std::optional<std::size_t> indice = cara_mayor(caras);
    if (!indice) {
        return std::nullopt;
    }
    const Caja& cara = caras[*indice];
    if (cara.h < cara_min) {
        return std::nullopt;
    }
    const Recorte recorte = calcular_recorte(cara, ancho_cuadro, alto_cuadro);
    if (recorte.ancho() <= 0 || recorte.alto() <= 0) {
        return std::nullopt;
    }
    return Eleccion{*indice, recorte};
}

}  // namespace accesia
