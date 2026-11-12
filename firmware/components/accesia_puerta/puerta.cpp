/**
 * Nombre: puerta.cpp
 * Descripción: Abre la puerta los segundos configurados con un temporizador y avisa cada cambio para publicarlo.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/puerta.hpp"

#include <mutex>

#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"

#include "accesia/puerta_logica.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "puerta";

std::mutex cerrojo;
PuertaLogica* logica = nullptr;
esp_timer_handle_t temporizador_cierre = nullptr;
void (*avisar_cambio)(bool) = nullptr;
int pin = PIN_NINGUNO;
bool activo_bajo = false;
bool en_led = false;

int64_t ahora_ms()
{
    return esp_timer_get_time() / 1000;
}

void manejar_salida(bool abierta)
{
    if (pin != PIN_NINGUNO && !en_led) {
        gpio_set_level(static_cast<gpio_num_t>(pin), abierta != activo_bajo ? 1 : 0);
    }
}

/// Aplica el cambio fuera del cerrojo: la salida y el aviso para publicarlo.
void cambio(bool abierta)
{
    manejar_salida(abierta);
    ESP_LOGI(TAG, "Puerta %s.", abierta ? "abierta" : "cerrada");
    if (avisar_cambio != nullptr) {
        avisar_cambio(abierta);
    }
}

void al_cumplir_tiempo(void*)
{
    bool cerro = false;
    {
        std::lock_guard<std::mutex> bloqueo(cerrojo);
        cerro = logica->actualizar(ahora_ms());
    }
    if (cerro) {
        cambio(false);
    }
}

}  // namespace

esp_err_t puerta_iniciar(const Config& config, int pin_compartido)
{
    logica = new PuertaLogica(config.puerta_segundos);
    pin = config.puerta_pin;
    activo_bajo = config.puerta_activo_bajo;
    en_led = pin != PIN_NINGUNO && pin == pin_compartido;

    if (pin != PIN_NINGUNO && !en_led) {
        ESP_RETURN_ON_ERROR(gpio_reset_pin(static_cast<gpio_num_t>(pin)), TAG, "Pin de la puerta inválido");
        ESP_RETURN_ON_ERROR(gpio_set_direction(static_cast<gpio_num_t>(pin), GPIO_MODE_OUTPUT), TAG,
                            "No se pudo usar el pin de la puerta");
        manejar_salida(false);
    }

    const esp_timer_create_args_t cierre = {
        .callback = al_cumplir_tiempo,
        .arg = nullptr,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "cierre_puerta",
        .skip_unhandled_events = false,
    };
    ESP_RETURN_ON_ERROR(esp_timer_create(&cierre, &temporizador_cierre), TAG, "Sin temporizador");

    if (pin == PIN_NINGUNO) {
        ESP_LOGI(TAG, "Puerta sin LED ni relé: solo publica su estado.");
    } else {
        ESP_LOGI(TAG, "Puerta en GPIO %d (%s), %d s, enciende en %s.", pin, en_led ? "el LED" : "salida propia",
                 config.puerta_segundos, activo_bajo ? "bajo" : "alto");
    }
    return ESP_OK;
}

void puerta_orden(bool abrir)
{
    bool cambio_estado = false;
    bool abierta = false;
    int64_t faltan_ms = 0;
    {
        std::lock_guard<std::mutex> bloqueo(cerrojo);
        const int64_t ahora = ahora_ms();
        cambio_estado = logica->orden(abrir ? OrdenPuerta::abrir : OrdenPuerta::cerrar, ahora);
        abierta = logica->abierta();
        faltan_ms = abierta ? logica->cierra_en_ms() - ahora : 0;
    }
    esp_timer_stop(temporizador_cierre);  // si no estaba corriendo, no pasa nada
    if (abierta) {
        esp_timer_start_once(temporizador_cierre, static_cast<uint64_t>(faltan_ms) * 1000);
    }
    if (cambio_estado) {
        cambio(abierta);
    }
}

bool puerta_abierta()
{
    std::lock_guard<std::mutex> bloqueo(cerrojo);
    return logica != nullptr && logica->abierta();
}

bool puerta_abierta_en_led()
{
    return en_led && puerta_abierta();
}

void puerta_al_cambiar(void (*avisar)(bool abierta))
{
    avisar_cambio = avisar;
}

}  // namespace accesia
