/**
 * Nombre: puerta_logica.cpp
 * Descripción: Órdenes de la puerta y cierre por tiempo (contratos/mqtt.md, «Temas»).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/puerta_logica.hpp"

namespace accesia {

OrdenPuerta leer_orden(std::string_view carga)
{
    if (carga == "ABRIR") {
        return OrdenPuerta::abrir;
    }
    if (carga == "CERRAR") {
        return OrdenPuerta::cerrar;
    }
    return OrdenPuerta::desconocida;
}

std::optional<bool> leer_activo_bajo(std::string_view texto)
{
    if (texto == "bajo") {
        return true;
    }
    if (texto == "alto") {
        return false;
    }
    return std::nullopt;
}

PuertaLogica::PuertaLogica(int segundos) : duracion_ms_(static_cast<std::int64_t>(segundos) * 1000) {}

bool PuertaLogica::orden(OrdenPuerta orden, std::int64_t ahora_ms)
{
    switch (orden) {
    case OrdenPuerta::abrir: {
        const bool cambia = !abierta_;
        abierta_ = true;
        cierra_en_ms_ = ahora_ms + duracion_ms_;
        return cambia;
    }
    case OrdenPuerta::cerrar: {
        const bool cambia = abierta_;
        abierta_ = false;
        return cambia;
    }
    case OrdenPuerta::desconocida:
        break;
    }
    return false;
}

bool PuertaLogica::actualizar(std::int64_t ahora_ms)
{
    if (abierta_ && ahora_ms >= cierra_en_ms_) {
        abierta_ = false;
        return true;
    }
    return false;
}

}  // namespace accesia
