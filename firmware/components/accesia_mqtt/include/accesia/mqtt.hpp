/**
 * Nombre: mqtt.hpp
 * Descripción: MQTT de la placa (contratos/mqtt.md 1.2): disponibilidad, estado, puerta, ambiente y descubrimiento de sus sensores.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <string>

#include "esp_err.h"

#include "accesia/config.hpp"

namespace accesia {

/// Funciones que la placa le da a MQTT. Las que falten no se usan.
struct EnlacesMqtt {
    void (*al_recibir_puerta)(bool abrir) = nullptr;  // con ABRIR o CERRAR en accesia/{codigo}/puerta/set
    bool (*puerta_abierta)() = nullptr;               // para publicar la puerta al conectarse
    std::string (*armar_estado)() = nullptr;          // el mensaje EstadoCamara, cada 60 s
    bool publica_ambiente = false;                    // si la placa publica el descubrimiento de sus sensores
};

/// Se conecta al broker con el código como client id y su último deseo en accesia/{codigo}/disponible. Al
/// conectarse publica «online», se suscribe a la puerta, publica el descubrimiento de sus sensores y su estado.
/// Sin código, sin dirección o sin clave no se conecta y lo explica por el monitor serial.
esp_err_t mqtt_iniciar(const Config& config, const EnlacesMqtt& enlaces);

bool mqtt_conectado();

/// accesia/{codigo}/puerta/estado: «abierta» o «cerrada», QoS 1, retenido.
void mqtt_publicar_puerta(bool abierta);

/// accesia/{codigo}/ambiente: el mensaje Ambiente, QoS 0, retenido.
void mqtt_publicar_ambiente(const std::string& mensaje);

/// Borra los dos config retenidos del descubrimiento de la placa, antes de cambiar de código (mqtt.md 1.2).
void mqtt_borrar_descubrimiento();

}  // namespace accesia
