/**
 * Nombre: config.cpp
 * Descripción: Lectura y escritura de la configuración de la placa en NVS, con valores de fábrica.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 *
 * Las claves del Wi-Fi y de MQTT y el token quedan en NVS sin cifrar: quien tenga la placa puede leerlos.
 * No se muestran por la consola.
 */

#include "accesia/config.hpp"

#include <cstdint>
#include <mutex>

#include "esp_app_desc.h"
#include "esp_check.h"
#include "esp_log.h"
#include "nvs.h"
#include "nvs_flash.h"

namespace accesia {
namespace {

constexpr const char* TAG = "config";
constexpr const char* ESPACIO = "accesia";  // espacio de nombres en NVS

std::mutex cerrojo;
Config actual;

bool leer_texto(nvs_handle_t nvs, const char* clave, std::string& destino)
{
    size_t largo = 0;
    if (nvs_get_str(nvs, clave, nullptr, &largo) != ESP_OK || largo == 0) {
        return false;
    }
    std::string valor(largo, '\0');
    if (nvs_get_str(nvs, clave, valor.data(), &largo) != ESP_OK) {
        return false;
    }
    valor.resize(largo - 1);  // sin el '\0' final
    destino = valor;
    return true;
}

void leer_entero(nvs_handle_t nvs, const char* clave, int& destino)
{
    int32_t valor = 0;
    if (nvs_get_i32(nvs, clave, &valor) == ESP_OK) {
        destino = static_cast<int>(valor);
    }
}

Config cargar(nvs_handle_t nvs)
{
    Config config;
    leer_texto(nvs, "wifi_ssid", config.wifi_ssid);
    leer_texto(nvs, "wifi_clave", config.wifi_clave);
    leer_texto(nvs, "servidor", config.servidor);
    leer_texto(nvs, "codigo", config.codigo);
    leer_texto(nvs, "token", config.token);
    leer_texto(nvs, "mqtt_url", config.mqtt_url);
    leer_texto(nvs, "mqtt_usuario", config.mqtt_usuario);
    leer_texto(nvs, "mqtt_clave", config.mqtt_clave);
    leer_entero(nvs, "puerta_pin", config.puerta_pin);
    leer_entero(nvs, "puerta_s", config.puerta_segundos);
    int activo_bajo = config.puerta_activo_bajo ? 1 : 0;
    leer_entero(nvs, "puerta_bajo", activo_bajo);
    config.puerta_activo_bajo = activo_bajo != 0;
    return config;
}

}  // namespace

esp_err_t config_iniciar()
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "La partición NVS cambió de formato: se borra y quedan los valores de fábrica.");
        ESP_RETURN_ON_ERROR(nvs_flash_erase(), TAG, "No se pudo borrar NVS");
        err = nvs_flash_init();
    }
    ESP_RETURN_ON_ERROR(err, TAG, "No se pudo iniciar NVS");

    nvs_handle_t nvs;
    err = nvs_open(ESPACIO, NVS_READONLY, &nvs);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        return ESP_OK;  // primera vez: no hay nada guardado
    }
    ESP_RETURN_ON_ERROR(err, TAG, "No se pudo abrir NVS");
    const Config cargada = cargar(nvs);
    nvs_close(nvs);

    std::lock_guard<std::mutex> bloqueo(cerrojo);
    actual = cargada;
    return ESP_OK;
}

Config config_leer()
{
    std::lock_guard<std::mutex> bloqueo(cerrojo);
    return actual;
}

esp_err_t config_guardar(const Config& nueva)
{
    nvs_handle_t nvs;
    ESP_RETURN_ON_ERROR(nvs_open(ESPACIO, NVS_READWRITE, &nvs), TAG, "No se pudo abrir NVS");

    esp_err_t err = ESP_OK;
    const auto texto = [&](const char* clave, const std::string& valor) {
        if (err == ESP_OK) {
            err = nvs_set_str(nvs, clave, valor.c_str());
        }
    };
    const auto entero = [&](const char* clave, int valor) {
        if (err == ESP_OK) {
            err = nvs_set_i32(nvs, clave, valor);
        }
    };

    texto("wifi_ssid", nueva.wifi_ssid);
    texto("wifi_clave", nueva.wifi_clave);
    texto("servidor", nueva.servidor);
    texto("codigo", nueva.codigo);
    texto("token", nueva.token);
    texto("mqtt_url", nueva.mqtt_url);
    texto("mqtt_usuario", nueva.mqtt_usuario);
    texto("mqtt_clave", nueva.mqtt_clave);
    entero("puerta_pin", nueva.puerta_pin);
    entero("puerta_s", nueva.puerta_segundos);
    entero("puerta_bajo", nueva.puerta_activo_bajo ? 1 : 0);
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo guardar la configuración: %s", esp_err_to_name(err));
        return err;
    }
    std::lock_guard<std::mutex> bloqueo(cerrojo);
    actual = nueva;
    return ESP_OK;
}

std::string config_texto(const char* clave, const char* por_defecto)
{
    std::string valor = por_defecto;
    nvs_handle_t nvs;
    if (nvs_open(ESPACIO, NVS_READONLY, &nvs) == ESP_OK) {
        leer_texto(nvs, clave, valor);
        nvs_close(nvs);
    }
    return valor;
}

esp_err_t config_guardar_texto(const char* clave, const std::string& valor)
{
    nvs_handle_t nvs;
    ESP_RETURN_ON_ERROR(nvs_open(ESPACIO, NVS_READWRITE, &nvs), TAG, "No se pudo abrir NVS");
    esp_err_t err = nvs_set_str(nvs, clave, valor.c_str());
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo guardar %s: %s", clave, esp_err_to_name(err));
    }
    return err;
}

std::string texto_firmware(const std::string& perfil)
{
    return "tinyml-" + (perfil.empty() ? std::string("sin_perfil") : perfil) + "-" + version_programa();
}

std::string version_programa()
{
    return esp_app_get_description()->version;
}

}  // namespace accesia
