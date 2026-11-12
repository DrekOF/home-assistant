/**
 * Nombre: ambiente_logica.hpp
 * Descripción: Lecturas del sensor de temperatura y humedad y qué publicar en cada una (mqtt.md 1.2, RF-14 · C3; lógica pura).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#pragma once

#include <optional>
#include <string>
#include <string_view>

#include "accesia/mensajes.hpp"

namespace accesia {

/// Cada cuánto se lee el sensor y se publica `ambiente` (mqtt.md 1.2).
inline constexpr int PERIODO_AMBIENTE_MS = 30000;

/// Fallas seguidas tras las que se publica null (mqtt.md 1.2).
inline constexpr int FALLAS_PARA_NULL = 3;

enum class TipoSensor { dht22, dht11 };

/// «dht22» o «dht11», como en el comando sensor y en EstadoCamara.
const char* nombre_sensor(TipoSensor tipo);

/// Lee «dht22» o «dht11». Otro texto, vacío.
std::optional<TipoSensor> leer_tipo_sensor(std::string_view texto);

/// true si la lectura cae en el rango que mide el sensor según su fabricante: el DHT22 de -40 a 80 °C y de 0 a
/// 100 %; el DHT11 de 0 a 50 °C y de 20 a 90 %. Fuera de rango cuenta como falla (por ejemplo, el tipo equivocado).
bool lectura_valida(TipoSensor tipo, double temperatura, double humedad);

/// Decide qué se publica después de cada intento de lectura.
class Ambiente {
public:
    /// Registra un intento. Devuelve el mensaje Ambiente a publicar, o vacío si esta vez no se publica:
    /// una lectura buena publica sus valores; una falla no publica, salvo desde la tercera seguida, que publica null.
    std::optional<std::string> registrar(bool leida, TipoSensor tipo, double temperatura, double humedad);

    int fallas_seguidas() const { return fallas_; }

    /// La última lectura buena, si hubo alguna.
    const std::optional<Lectura>& ultima() const { return ultima_; }

private:
    int fallas_ = 0;
    std::optional<Lectura> ultima_;
};

}  // namespace accesia
