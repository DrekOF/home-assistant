/**
 * Nombre: placa.cpp
 * Descripción: Antena (GPIO3 y GPIO14), LED de estado y puerta (GPIO15, enciende en bajo) y comando antena de la XIAO ESP32-C6.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Pines de la wiki de Seeed (wiki.seeedstudio.com/xiao_esp32c6_getting_started), por verificar con la placa.
 */

#include "accesia/placa.hpp"

#include <atomic>
#include <cstdio>

#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "accesia/config.hpp"
#include "accesia/consola.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "placa";
constexpr const char* CLAVE_ANTENA = "antena";
constexpr int PERIODO_LED_MS = 50;
constexpr uint32_t PILA_LED = 2048;

std::atomic<Antena> antena_actual{Antena::interna};
bool (*puerta_en_led)() = nullptr;
Conexion (*estado_conexion)() = nullptr;

esp_err_t salida(int pin, int nivel)
{
    const gpio_num_t gpio = static_cast<gpio_num_t>(pin);
    ESP_RETURN_ON_ERROR(gpio_reset_pin(gpio), TAG, "GPIO %d inválido", pin);
    ESP_RETURN_ON_ERROR(gpio_set_direction(gpio, GPIO_MODE_OUTPUT), TAG, "GPIO %d sin salida", pin);
    return gpio_set_level(gpio, nivel);
}

void aplicar_antena(Antena antena)
{
    // GPIO14: en bajo la antena cerámica interna; en alto la externa U.FL.
    gpio_set_level(static_cast<gpio_num_t>(PIN_ANTENA), antena == Antena::externa ? 1 : 0);
    antena_actual = antena;
}

void tarea_led(void*)
{
    for (;;) {
        const bool puerta = puerta_en_led != nullptr && puerta_en_led();
        const Conexion conexion = estado_conexion != nullptr ? estado_conexion() : Conexion::conectada;
        const bool encendido = led_encendido(puerta, conexion, esp_timer_get_time() / 1000);
        gpio_set_level(static_cast<gpio_num_t>(PIN_LED), encendido ? 0 : 1);  // enciende en bajo
        vTaskDelay(pdMS_TO_TICKS(PERIODO_LED_MS));
    }
}

int cmd_antena(int argc, char** argv)
{
    const std::optional<Antena> antena = argc == 2 ? leer_antena(argv[1]) : std::nullopt;
    if (!antena) {
        printf("Uso: antena <interna|externa>   la de fábrica es la interna\n");
        return 1;
    }
    if (config_guardar_texto(CLAVE_ANTENA, nombre_antena(*antena)) != ESP_OK) {
        printf("No se pudo guardar en NVS.\n");
        return 1;
    }
    aplicar_antena(*antena);
    printf("Antena %s: ya está en uso y queda guardada.\n", nombre_antena(*antena));
    return 0;
}

void escribir_estado()
{
    printf("Placa:     XIAO ESP32-C6, firmware %s\n", texto_firmware(PERFIL_C6).c_str());
    printf("Antena:    %s (GPIO%d en %s)\n", nombre_antena(antena_actual), PIN_ANTENA,
           antena_actual == Antena::externa ? "alto" : "bajo");
}

}  // namespace

esp_err_t placa_elegir_antena()
{
    // GPIO3 en bajo enciende el conmutador de antena; después GPIO14 elige cuál.
    ESP_RETURN_ON_ERROR(salida(PIN_CONMUTADOR, 0), TAG, "No se pudo encender el conmutador de antena");
    ESP_RETURN_ON_ERROR(salida(PIN_ANTENA, 0), TAG, "No se pudo elegir la antena");
    const std::string guardada = config_texto(CLAVE_ANTENA, nombre_antena(Antena::interna));
    aplicar_antena(leer_antena(guardada).value_or(Antena::interna));
    ESP_LOGI(TAG, "Antena %s.", nombre_antena(antena_actual));
    return ESP_OK;
}

esp_err_t placa_iniciar(bool (*puerta_abierta_en_led)(), Conexion (*conexion)())
{
    puerta_en_led = puerta_abierta_en_led;
    estado_conexion = conexion;
    consola_registrar("antena", "antena <interna|externa>", "antena externa", cmd_antena);
    consola_agregar_estado(escribir_estado);
    consola_revisar_gpio(gpio_utilizable_c6);

    ESP_RETURN_ON_ERROR(salida(PIN_LED, 1), TAG, "No se pudo usar el LED");  // apagado: enciende en bajo
    const BaseType_t creada = xTaskCreate(tarea_led, "led", PILA_LED, nullptr, 1, nullptr);
    ESP_RETURN_ON_FALSE(creada == pdPASS, ESP_ERR_NO_MEM, TAG, "No se pudo crear la tarea del LED");
    return ESP_OK;
}

Antena placa_antena()
{
    return antena_actual;
}

}  // namespace accesia
