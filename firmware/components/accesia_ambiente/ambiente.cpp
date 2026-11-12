/**
 * Nombre: ambiente.cpp
 * Descripción: Tarea que lee el DHT22 o DHT11 con esp-idf-lib/dht cada 30 s y publica el mensaje Ambiente (mqtt.md 1.2).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/ambiente.hpp"

#include <atomic>
#include <cstdio>
#include <mutex>

#include "dht.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "accesia/config.hpp"
#include "accesia/consola.hpp"
#include "accesia/placa_c6.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "ambiente";
constexpr const char* CLAVE_SENSOR = "sensor";
constexpr int ESPERA_INICIAL_MS = 2000;  // el DHT necesita un momento después de encender
constexpr uint32_t PILA = 4096;

std::atomic<TipoSensor> tipo_actual{TipoSensor::dht22};
std::mutex cerrojo;
Ambiente logica;
int64_t ultima_lectura_us = 0;
void (*publicar_mensaje)(const std::string&) = nullptr;

void tarea(void*)
{
    vTaskDelay(pdMS_TO_TICKS(ESPERA_INICIAL_MS));
    for (;;) {
        const TipoSensor tipo = tipo_actual;
        float humedad = 0.0f;
        float temperatura = 0.0f;
        const esp_err_t err =
            dht_read_float_data(tipo == TipoSensor::dht22 ? DHT_TYPE_AM2301 : DHT_TYPE_DHT11,
                                static_cast<gpio_num_t>(PIN_DHT), &humedad, &temperatura);
        std::optional<std::string> mensaje;
        int fallas = 0;
        {
            std::lock_guard<std::mutex> bloqueo(cerrojo);
            mensaje = logica.registrar(err == ESP_OK, tipo, temperatura, humedad);
            fallas = logica.fallas_seguidas();
            if (fallas == 0) {
                ultima_lectura_us = esp_timer_get_time();
            }
        }
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "No se pudo leer el %s en GPIO%d: %s (%d seguidas).", nombre_sensor(tipo), PIN_DHT,
                     esp_err_to_name(err), fallas);
        } else if (fallas > 0) {
            ESP_LOGW(TAG, "Lectura fuera del rango del %s: %.1f °C y %.1f %%. ¿Es el tipo de sensor correcto?",
                     nombre_sensor(tipo), static_cast<double>(temperatura), static_cast<double>(humedad));
        }
        if (mensaje && publicar_mensaje != nullptr) {
            publicar_mensaje(*mensaje);
        }
        vTaskDelay(pdMS_TO_TICKS(PERIODO_AMBIENTE_MS));
    }
}

int cmd_sensor(int argc, char** argv)
{
    const std::optional<TipoSensor> tipo = argc == 2 ? leer_tipo_sensor(argv[1]) : std::nullopt;
    if (!tipo) {
        printf("Uso: sensor <dht22|dht11>   el de fábrica es dht22\n");
        return 1;
    }
    if (config_guardar_texto(CLAVE_SENSOR, nombre_sensor(*tipo)) != ESP_OK) {
        printf("No se pudo guardar en NVS.\n");
        return 1;
    }
    tipo_actual = *tipo;
    printf("Sensor: %s. Se usa desde la siguiente lectura.\n", nombre_sensor(*tipo));
    return 0;
}

void escribir_estado()
{
    std::lock_guard<std::mutex> bloqueo(cerrojo);
    const char* nombre = nombre_sensor(tipo_actual);
    if (const auto& lectura = logica.ultima(); lectura && logica.fallas_seguidas() == 0) {
        const long long hace_s = (esp_timer_get_time() - ultima_lectura_us) / 1000000;
        printf("Sensor:    %s en GPIO%d, %.1f °C y %.1f %% (hace %lld s)\n", nombre, PIN_DHT, lectura->temperatura,
               lectura->humedad, hace_s);
    } else if (logica.fallas_seguidas() > 0) {
        printf("Sensor:    %s en GPIO%d, %d lecturas fallidas seguidas\n", nombre, PIN_DHT, logica.fallas_seguidas());
    } else {
        printf("Sensor:    %s en GPIO%d, sin lectura todavía\n", nombre, PIN_DHT);
    }
}

}  // namespace

esp_err_t ambiente_iniciar(void (*publicar)(const std::string& mensaje))
{
    publicar_mensaje = publicar;
    const std::string guardado = config_texto(CLAVE_SENSOR, nombre_sensor(TipoSensor::dht22));
    tipo_actual = leer_tipo_sensor(guardado).value_or(TipoSensor::dht22);

    consola_registrar("sensor", "sensor <dht22|dht11>", "sensor dht11", cmd_sensor);
    consola_agregar_estado(escribir_estado);

    const BaseType_t creada = xTaskCreate(tarea, "ambiente", PILA, nullptr, 3, nullptr);
    ESP_RETURN_ON_FALSE(creada == pdPASS, ESP_ERR_NO_MEM, TAG, "No se pudo crear la tarea del sensor");
    ESP_LOGI(TAG, "Sensor %s en GPIO%d, cada %d s.", nombre_sensor(tipo_actual), PIN_DHT, PERIODO_AMBIENTE_MS / 1000);
    return ESP_OK;
}

TipoSensor ambiente_tipo()
{
    return tipo_actual;
}

}  // namespace accesia
