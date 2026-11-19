/**
 * Nombre: consola.hpp
 * Descripción: Consola serial de la placa, por UART0 y, si lo tiene, por el USB nativo: comandos comunes y los que registra cada componente.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.2
 */

#pragma once

#include <string>

#include "esp_console.h"
#include "esp_err.h"

namespace accesia {

/// Registra los comandos comunes (arquitectura.md, «Consola serial») y arranca las tareas que los leen: una por
/// UART0 y, en la XIAO ESP32-C6, otra por el USB Serial/JTAG. La ESP32-CAM solo tiene UART0.
esp_err_t consola_iniciar();

/// Suma el comando de un componente, como «sensor» o «antena». «uso» y «ejemplo» salen en «ayuda».
void consola_registrar(const char* comando, const char* uso, const char* ejemplo, esp_console_cmd_func_t funcion);

/// Suma líneas al comando «estado»: la función las escribe con printf.
void consola_agregar_estado(void (*escribir_lineas)());

/// Se llama antes de guardar un código nuevo, con la conexión todavía en el código viejo: ahí la placa borra su
/// descubrimiento retenido, porque con el código nuevo la ACL ya no la deja (mqtt.md 1.2).
void consola_antes_de_cambiar_codigo(void (*antes)());

/// Revisa si un GPIO sirve para la puerta en esta placa. Sin revisor, se acepta cualquiera desde 0.
void consola_revisar_gpio(bool (*utilizable)(int gpio, std::string& motivo));

}  // namespace accesia
