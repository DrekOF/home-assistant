/**
 * Nombre: recorte.hpp
 * Descripción: Elección de la cara y fórmula del recorte del contrato api-dispositivo.md (lógica pura, sin hardware).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <cstddef>
#include <optional>
#include <vector>

namespace accesia {

/// Caja de una cara: esquina superior izquierda, ancho y alto, en píxeles del cuadro.
struct Caja {
    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;
};

/// Recorte de (x0, y0) a (x1, y1), sin incluir x1 ni y1.
struct Recorte {
    int x0 = 0;
    int y0 = 0;
    int x1 = 0;
    int y1 = 0;

    int ancho() const { return x1 - x0; }
    int alto() const { return y1 - y0; }
};

/// Cara que la cámara enviaría y su recorte.
struct Eleccion {
    std::size_t indice = 0;
    Recorte recorte;
};

/// Índice de la cara de mayor área. Con empate gana la primera, que en ESP-DL es la de mayor puntaje.
/// No cuenta las cajas sin ancho o sin alto. Vacío si no queda ninguna.
std::optional<std::size_t> cara_mayor(const std::vector<Caja>& caras);

/// Fórmula del recorte (api-dispositivo.md): 25 % de margen por lado, cortado en los bordes del cuadro.
///   x0 = max(0, piso(x - w/4))        y0 = max(0, piso(y - h/4))
///   x1 = min(W, techo(x + w + w/4))   y1 = min(H, techo(y + h + h/4))
Recorte calcular_recorte(const Caja& cara, int ancho_cuadro, int alto_cuadro);

/// Lo que la cámara enviaría: la cara de mayor área con su recorte, solo si mide al menos cara_min de alto
/// (RF-01 · C3). Vacío si no hay caras, si la de mayor área es más baja que cara_min o si el recorte queda vacío.
std::optional<Eleccion> elegir_recorte(const std::vector<Caja>& caras, int ancho_cuadro, int alto_cuadro,
                                       int cara_min);

}  // namespace accesia
