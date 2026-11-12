/**
 * Nombre: consola.hpp
 * Descripción: Consola serial de la cámara con los comandos de arquitectura.md, por UART0 y por el USB nativo.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include "esp_err.h"

namespace accesia {

/// Registra los comandos y arranca las dos tareas que los leen: una por UART0 y otra por el USB Serial/JTAG.
esp_err_t consola_iniciar();

}  // namespace accesia
