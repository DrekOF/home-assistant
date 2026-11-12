/**
 * Nombre: ambiente_logica.cpp
 * Descripción: Rangos de los sensores DHT22 y DHT11, y la regla de las 3 fallas seguidas antes de publicar null.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/ambiente_logica.hpp"

namespace accesia {

const char* nombre_sensor(TipoSensor tipo)
{
    return tipo == TipoSensor::dht22 ? "dht22" : "dht11";
}

std::optional<TipoSensor> leer_tipo_sensor(std::string_view texto)
{
    if (texto == "dht22") {
        return TipoSensor::dht22;
    }
    if (texto == "dht11") {
        return TipoSensor::dht11;
    }
    return std::nullopt;
}

bool lectura_valida(TipoSensor tipo, double temperatura, double humedad)
{
    if (tipo == TipoSensor::dht22) {
        return temperatura >= -40.0 && temperatura <= 80.0 && humedad >= 0.0 && humedad <= 100.0;
    }
    return temperatura >= 0.0 && temperatura <= 50.0 && humedad >= 20.0 && humedad <= 90.0;
}

std::optional<std::string> Ambiente::registrar(bool leida, TipoSensor tipo, double temperatura, double humedad)
{
    if (leida && lectura_valida(tipo, temperatura, humedad)) {
        fallas_ = 0;
        ultima_ = Lectura{temperatura, humedad};
        return mensaje_ambiente(ultima_);
    }
    ++fallas_;
    if (fallas_ >= FALLAS_PARA_NULL) {
        return mensaje_ambiente(std::nullopt);
    }
    return std::nullopt;
}

}  // namespace accesia
