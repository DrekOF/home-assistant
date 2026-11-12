/**
 * Nombre: led.hpp
 * Descripción: Qué muestra el LED de la placa: la puerta manda; si no, el estado de la conexión (RF-14 · C5; lógica pura).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <cstdint>

namespace accesia {

enum class Conexion { sin_wifi, sin_broker, conectada };

/// Medio periodo del parpadeo: lento sin Wi-Fi y rápido sin broker.
inline constexpr std::int64_t PARPADEO_SIN_WIFI_MS = 500;
inline constexpr std::int64_t PARPADEO_SIN_BROKER_MS = 150;

/// true si el LED va encendido en este instante. Con la puerta abierta, siempre; si no, parpadea lento sin Wi-Fi,
/// rápido sin broker, y queda apagado con todo conectado.
bool led_encendido(bool puerta_abierta, Conexion conexion, std::int64_t ahora_ms);

}  // namespace accesia
