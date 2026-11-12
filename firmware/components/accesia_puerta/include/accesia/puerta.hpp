/**
 * Nombre: puerta.hpp
 * Descripción: Salida de la puerta de la placa: un LED o un relé, con su nivel activo y sus segundos (mqtt.md, RF-14 · C5).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include "esp_err.h"

#include "accesia/config.hpp"

namespace accesia {

/// Prepara la puerta con el pin, el nivel y los segundos de la configuración. Si el pin es pin_compartido (el LED
/// de estado de la placa), no lo maneja: el LED muestra la puerta abierta (placa_iniciar_led).
esp_err_t puerta_iniciar(const Config& config, int pin_compartido);

/// Aplica ABRIR (true) o CERRAR (false). Se llama desde MQTT.
void puerta_orden(bool abrir);

bool puerta_abierta();

/// true si la puerta está abierta y su salida es el LED compartido.
bool puerta_abierta_en_led();

/// Se llama cada vez que la puerta cambia de estado, para publicarlo.
void puerta_al_cambiar(void (*avisar)(bool abierta));

}  // namespace accesia
