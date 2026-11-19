/**
 * Nombre: mqtt.cpp
 * Descripción: Cliente MQTT de la placa con esp-mqtt: temas y mensajes de contratos/mqtt.md 1.6.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

#include "accesia/mqtt.hpp"

#include <atomic>
#include <cstdio>
#include <initializer_list>
#include <string_view>

#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mqtt_client.h"

#include "accesia/consola.hpp"
#include "accesia/mensajes.hpp"
#include "accesia/puerta_logica.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "mqtt";
constexpr uint64_t PERIODO_ESTADO_US = 60ULL * 1000 * 1000;  // EstadoCamara cada 60 s (mqtt.md)

esp_mqtt_client_handle_t cliente = nullptr;
std::atomic<bool> conectado{false};
EnlacesMqtt enlaces_actuales;
esp_timer_handle_t temporizador_estado = nullptr;

// esp-mqtt guarda punteros a estos textos: viven mientras viva el cliente.
std::string url;
std::string usuario;
std::string clave;
std::string codigo;
std::string tema_disponible;
std::string tema_puerta_set;
std::string tema_puerta_estado;
std::string tema_estado;
std::string tema_ambiente;
std::string tema_presencia;
std::string motivo_sin_mqtt;

void publicar(const std::string& tema, const std::string& carga, int qos, bool retenido)
{
    if (cliente == nullptr || !conectado) {
        return;
    }
    esp_mqtt_client_publish(cliente, tema.c_str(), carga.c_str(), static_cast<int>(carga.size()), qos,
                            retenido ? 1 : 0);
}

void publicar_estado()
{
    if (enlaces_actuales.armar_estado != nullptr) {
        publicar(tema_estado, enlaces_actuales.armar_estado(), 0, true);
    }
}

void publicar_descubrimiento()
{
    const std::string version = version_programa();
    if (enlaces_actuales.publica_presencia) {
        publicar(tema_descubrimiento_presencia(codigo), mensaje_descubrimiento_presencia(codigo, version), 1, true);
    }
    if (enlaces_actuales.publica_ambiente) {
        for (const SensorAmbiente sensor : {SensorAmbiente::temperatura, SensorAmbiente::humedad}) {
            publicar(tema_descubrimiento(codigo, sensor), mensaje_descubrimiento(codigo, sensor, version), 1, true);
        }
    }
}

/// La presencia de ahora, retenida, cada vez que se conecta (mqtt.md 1.6).
void publicar_presencia_actual()
{
    if (enlaces_actuales.publica_presencia && enlaces_actuales.armar_presencia != nullptr) {
        publicar(tema_presencia, enlaces_actuales.armar_presencia(), 1, true);
    }
}

void al_cumplir_periodo(void*)
{
    publicar_estado();
}

void al_evento(void*, esp_event_base_t, int32_t id, void* datos)
{
    const auto* evento = static_cast<esp_mqtt_event_handle_t>(datos);
    switch (static_cast<esp_mqtt_event_id_t>(id)) {
    case MQTT_EVENT_CONNECTED:
        conectado = true;
        ESP_LOGI(TAG, "Conectado al broker como %s.", codigo.c_str());
        publicar(tema_disponible, "online", 1, true);
        esp_mqtt_client_subscribe(cliente, tema_puerta_set.c_str(), 1);
        publicar_descubrimiento();
        publicar_presencia_actual();
        if (enlaces_actuales.puerta_abierta != nullptr) {
            publicar(tema_puerta_estado, enlaces_actuales.puerta_abierta() ? "abierta" : "cerrada", 1, true);
        }
        publicar_estado();
        break;
    case MQTT_EVENT_DISCONNECTED:
        if (conectado) {
            ESP_LOGW(TAG, "Se perdió la conexión con el broker; esp-mqtt reintenta solo.");
        }
        conectado = false;
        break;
    case MQTT_EVENT_DATA:
        if (evento->topic_len > 0 &&
            std::string_view(evento->topic, static_cast<size_t>(evento->topic_len)) == tema_puerta_set &&
            enlaces_actuales.al_recibir_puerta != nullptr) {
            const OrdenPuerta orden = leer_orden(std::string_view(evento->data, static_cast<size_t>(evento->data_len)));
            if (orden != OrdenPuerta::desconocida) {
                enlaces_actuales.al_recibir_puerta(orden == OrdenPuerta::abrir);
            }
        }
        break;
    case MQTT_EVENT_ERROR:
        ESP_LOGW(TAG, "Error de MQTT: revisa la dirección, el usuario y la clave del broker.");
        break;
    default:
        break;
    }
}

void escribir_estado()
{
    if (cliente == nullptr) {
        printf("Broker:    sin conectar (%s)\n", motivo_sin_mqtt.c_str());
    } else {
        printf("Broker:    %s, como %s\n", conectado ? "conectado" : "conectando", codigo.c_str());
    }
}

}  // namespace

esp_err_t mqtt_iniciar(const Config& config, const EnlacesMqtt& enlaces)
{
    consola_agregar_estado(escribir_estado);
    enlaces_actuales = enlaces;
    if (config.codigo.empty()) {
        motivo_sin_mqtt = "falta el código";
    } else if (config.mqtt_url.empty() || config.mqtt_clave.empty()) {
        motivo_sin_mqtt = "falta el broker o su clave";
    }
    if (!motivo_sin_mqtt.empty()) {
        ESP_LOGW(TAG, "Sin MQTT: %s. Configúralo con «codigo» y «mqtt», y reinicia.", motivo_sin_mqtt.c_str());
        return ESP_OK;
    }

    url = config.mqtt_url;
    usuario = config.mqtt_usuario;
    clave = config.mqtt_clave;
    codigo = config.codigo;
    tema_disponible = tema(codigo, "disponible");
    tema_puerta_set = tema(codigo, "puerta/set");
    tema_puerta_estado = tema(codigo, "puerta/estado");
    tema_estado = tema(codigo, "estado");
    tema_ambiente = tema(codigo, "ambiente");
    tema_presencia = tema(codigo, "presencia");

    esp_mqtt_client_config_t configuracion = {};
    configuracion.broker.address.uri = url.c_str();
    configuracion.credentials.username = usuario.c_str();
    configuracion.credentials.client_id = codigo.c_str();  // la ACL exige el código como client id
    configuracion.credentials.authentication.password = clave.c_str();
    configuracion.session.last_will.topic = tema_disponible.c_str();
    configuracion.session.last_will.msg = "offline";
    configuracion.session.last_will.msg_len = 7;
    configuracion.session.last_will.qos = 1;
    configuracion.session.last_will.retain = 1;
    configuracion.session.keepalive = 30;
    configuracion.network.reconnect_timeout_ms = 5000;

    cliente = esp_mqtt_client_init(&configuracion);
    ESP_RETURN_ON_FALSE(cliente != nullptr, ESP_FAIL, TAG, "No se pudo crear el cliente MQTT");
    ESP_RETURN_ON_ERROR(esp_mqtt_client_register_event(cliente, MQTT_EVENT_ANY, al_evento, nullptr), TAG,
                        "Sin eventos de MQTT");

    const esp_timer_create_args_t periodo = {
        .callback = al_cumplir_periodo,
        .arg = nullptr,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "estado_mqtt",
        .skip_unhandled_events = true,
    };
    ESP_RETURN_ON_ERROR(esp_timer_create(&periodo, &temporizador_estado), TAG, "Sin temporizador");
    ESP_RETURN_ON_ERROR(esp_timer_start_periodic(temporizador_estado, PERIODO_ESTADO_US), TAG, "Sin temporizador");

    ESP_RETURN_ON_ERROR(esp_mqtt_client_start(cliente), TAG, "No se pudo arrancar MQTT");
    ESP_LOGI(TAG, "Conectando a %s como %s...", url.c_str(), codigo.c_str());
    return ESP_OK;
}

bool mqtt_conectado()
{
    return conectado;
}

void mqtt_publicar_puerta(bool abierta)
{
    publicar(tema_puerta_estado, abierta ? "abierta" : "cerrada", 1, true);
}

void mqtt_publicar_ambiente(const std::string& mensaje)
{
    publicar(tema_ambiente, mensaje, 0, true);
}

void mqtt_publicar_presencia(const std::string& mensaje)
{
    publicar(tema_presencia, mensaje, 1, true);
}

void mqtt_borrar_descubrimiento()
{
    if (!enlaces_actuales.publica_ambiente && !enlaces_actuales.publica_presencia) {
        return;
    }
    if (!conectado) {
        printf("Sin conexión al broker: el descubrimiento retenido del código %s queda; bórralo a mano (mqtt.md).\n",
               codigo.empty() ? "anterior" : codigo.c_str());
        return;
    }
    // Un mensaje vacío y retenido borra el config retenido.
    if (enlaces_actuales.publica_presencia) {
        esp_mqtt_client_publish(cliente, tema_descubrimiento_presencia(codigo).c_str(), "", 0, 1, 1);
    }
    if (enlaces_actuales.publica_ambiente) {
        for (const SensorAmbiente sensor : {SensorAmbiente::temperatura, SensorAmbiente::humedad}) {
            esp_mqtt_client_publish(cliente, tema_descubrimiento(codigo, sensor).c_str(), "", 0, 1, 1);
        }
    }
    vTaskDelay(pdMS_TO_TICKS(300));  // que alcancen a salir antes de guardar el código nuevo
    printf("Se borró el descubrimiento del código %s.\n", codigo.c_str());
}

}  // namespace accesia
