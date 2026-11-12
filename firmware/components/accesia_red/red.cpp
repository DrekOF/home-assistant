/**
 * Nombre: red.cpp
 * Descripción: Conexión Wi-Fi de la placa, su IP y su RSSI, con reintentos crecientes y la línea de «estado».
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/red.hpp"

#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <mutex>

#include "esp_check.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"

#include "accesia/consola.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "red";
constexpr int ESPERA_MAXIMA_S = 10;

std::atomic<bool> conectada{false};
std::mutex cerrojo_ip;
std::string ip_actual;
std::string red_configurada;
int intentos = 0;
esp_timer_handle_t temporizador_reintento = nullptr;

void reintentar(void*)
{
    esp_wifi_connect();
}

void al_evento(void*, esp_event_base_t base, int32_t id, void* datos)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        conectada = false;
        {
            std::lock_guard<std::mutex> bloqueo(cerrojo_ip);
            ip_actual.clear();
        }
        // 1, 2, 4, 8 y después 10 s entre intentos.
        const int espera_s = std::min(ESPERA_MAXIMA_S, 1 << std::min(intentos, 4));
        ++intentos;
        ESP_LOGW(TAG, "Sin Wi-Fi en %s; reintento en %d s.", red_configurada.c_str(), espera_s);
        esp_timer_start_once(temporizador_reintento, static_cast<uint64_t>(espera_s) * 1000000);
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        const auto* evento = static_cast<const ip_event_got_ip_t*>(datos);
        char texto[16];
        std::snprintf(texto, sizeof(texto), IPSTR, IP2STR(&evento->ip_info.ip));
        {
            std::lock_guard<std::mutex> bloqueo(cerrojo_ip);
            ip_actual = texto;
        }
        intentos = 0;
        conectada = true;
        ESP_LOGI(TAG, "Wi-Fi conectado a %s con la IP %s.", red_configurada.c_str(), texto);
    }
}

// Copia un texto a un campo de wifi_config_t, que ya viene en ceros. ESP-IDF acepta un SSID de 32 bytes sin el cero
// final; la consola ya limita el SSID a 32 bytes y la clave a 63 caracteres.
void copiar_campo(uint8_t* destino, std::size_t tamano, const std::string& texto)
{
    std::memcpy(destino, texto.data(), std::min(tamano, texto.size()));
}

void escribir_estado()
{
    const std::optional<int> rssi = red_rssi();
    if (red_conectada() && rssi) {
        printf("IP:        %s, señal %d dBm\n", red_ip().c_str(), *rssi);
    } else {
        printf("IP:        sin conexión a %s\n", red_configurada.empty() ? "ninguna red" : red_configurada.c_str());
    }
}

}  // namespace

esp_err_t red_iniciar(const Config& config)
{
    red_configurada = config.wifi_ssid;
    consola_agregar_estado(escribir_estado);
    if (config.wifi_ssid.empty() || config.wifi_clave.empty()) {
        ESP_LOGW(TAG, "Falta el Wi-Fi: configúralo con «wifi <ssid> <clave>» y reinicia.");
        return ESP_OK;
    }

    ESP_RETURN_ON_ERROR(esp_netif_init(), TAG, "No se pudo iniciar esp_netif");
    const esp_err_t bucle = esp_event_loop_create_default();
    ESP_RETURN_ON_FALSE(bucle == ESP_OK || bucle == ESP_ERR_INVALID_STATE, bucle, TAG, "Sin bucle de eventos");
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t inicio = WIFI_INIT_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_wifi_init(&inicio), TAG, "No se pudo iniciar el Wi-Fi");
    ESP_RETURN_ON_ERROR(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, al_evento, nullptr, nullptr),
                        TAG, "Sin eventos de Wi-Fi");
    ESP_RETURN_ON_ERROR(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, al_evento, nullptr, nullptr),
                        TAG, "Sin eventos de IP");

    const esp_timer_create_args_t reintento = {
        .callback = reintentar,
        .arg = nullptr,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "reintento_wifi",
        .skip_unhandled_events = true,
    };
    ESP_RETURN_ON_ERROR(esp_timer_create(&reintento, &temporizador_reintento), TAG, "Sin temporizador");

    wifi_config_t wifi = {};
    copiar_campo(wifi.sta.ssid, sizeof(wifi.sta.ssid), config.wifi_ssid);
    copiar_campo(wifi.sta.password, sizeof(wifi.sta.password), config.wifi_clave);
    wifi.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;

    ESP_RETURN_ON_ERROR(esp_wifi_set_mode(WIFI_MODE_STA), TAG, "No se pudo poner el modo estación");
    ESP_RETURN_ON_ERROR(esp_wifi_set_config(WIFI_IF_STA, &wifi), TAG, "No se pudo configurar la red");
    ESP_RETURN_ON_ERROR(esp_wifi_start(), TAG, "No se pudo encender el Wi-Fi");
    // Sin ahorro de energía: la placa va al USB y así la orden de la puerta llega sin esperar.
    esp_wifi_set_ps(WIFI_PS_NONE);
    ESP_LOGI(TAG, "Conectando a %s...", config.wifi_ssid.c_str());
    return ESP_OK;
}

bool red_conectada()
{
    return conectada;
}

std::string red_ip()
{
    std::lock_guard<std::mutex> bloqueo(cerrojo_ip);
    return ip_actual;
}

std::optional<int> red_rssi()
{
    if (!conectada) {
        return std::nullopt;
    }
    wifi_ap_record_t punto = {};
    if (esp_wifi_sta_get_ap_info(&punto) != ESP_OK) {
        return std::nullopt;
    }
    return punto.rssi;
}

}  // namespace accesia
