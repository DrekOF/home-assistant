/**
 * Nombre: puerta_logica.hpp
 * Descripción: Puerta de la placa (mqtt.md): ABRIR la abre los segundos configurados y CERRAR la cierra antes (lógica pura).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <cstdint>
#include <optional>
#include <string_view>

namespace accesia {

enum class OrdenPuerta { abrir, cerrar, desconocida };

/// Lee la carga de accesia/{codigo}/puerta/set: «ABRIR» o «CERRAR». Cualquier otra cosa es desconocida.
OrdenPuerta leer_orden(std::string_view carga);

/// Lee el nivel que enciende la salida de la puerta: «bajo» devuelve true y «alto», false. Otro texto, vacío.
std::optional<bool> leer_activo_bajo(std::string_view texto);

/// Estado de la puerta en el tiempo. Los tiempos son milisegundos de un reloj que solo avanza.
class PuertaLogica {
public:
    explicit PuertaLogica(int segundos);

    /// Aplica una orden. Devuelve true si la puerta cambió de estado, y entonces hay que publicarlo.
    /// ABRIR con la puerta abierta vuelve a contar los segundos sin cambiar el estado.
    bool orden(OrdenPuerta orden, std::int64_t ahora_ms);

    /// Cierra la puerta cuando se cumplen los segundos. Devuelve true si se cerró en esta llamada.
    bool actualizar(std::int64_t ahora_ms);

    bool abierta() const { return abierta_; }

    /// Instante en que se cierra sola, o -1 si está cerrada.
    std::int64_t cierra_en_ms() const { return abierta_ ? cierra_en_ms_ : -1; }

private:
    std::int64_t duracion_ms_;
    bool abierta_ = false;
    std::int64_t cierra_en_ms_ = 0;
};

}  // namespace accesia
