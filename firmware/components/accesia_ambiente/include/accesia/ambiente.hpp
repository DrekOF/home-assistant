/**
 * Nombre: ambiente.hpp
 * Descripción: Sensor de temperatura y humedad de la placa (DHT22 o DHT11 en GPIO2), leído cada 30 s (RF-14 · C3).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <string>

#include "esp_err.h"

#include "accesia/ambiente_logica.hpp"

namespace accesia {

/// Lee el tipo de sensor guardado (DHT22 de fábrica), registra el comando «sensor» y su línea de «estado», y
/// arranca la tarea que lee cada 30 s. Llamar después de consola_iniciar.
esp_err_t ambiente_iniciar(void (*publicar)(const std::string& mensaje));

/// Tipo de sensor configurado.
TipoSensor ambiente_tipo();

}  // namespace accesia
