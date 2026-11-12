/**
 * Nombre: config.cpp
 * Descripción: Lectura y escritura de la configuración de la cámara en NVS, con valores por defecto.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
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

void leer_texto(nvs_handle_t nvs, const char* clave, std::string& destino)
{
    size_t largo = 0;
    if (nvs_get_str(nvs, clave, nullptr, &largo) != ESP_OK || largo == 0) {
        return;
    }
    std::string valor(largo, '\0');
    if (nvs_get_str(nvs, clave, valor.data(), &largo) == ESP_OK) {
        valor.resize(largo - 1);  // sin el '\0' final
        destino = valor;
    }
}

void leer_entero(nvs_handle_t nvs, const char* clave, int& destino)
{
    int32_t valor = 0;
    if (nvs_get_i32(nvs, clave, &valor) == ESP_OK) {
        destino = static_cast<int>(valor);
    }
}

void leer_pines(nvs_handle_t nvs, PinesCamara& destino)
{
    size_t largo = 0;
    if (nvs_get_blob(nvs, "pines", nullptr, &largo) != ESP_OK || largo != sizeof(PinesCamara)) {
        return;  // sin guardar, o guardado por otra versión: quedan sin definir
    }
    PinesCamara pines;
    if (nvs_get_blob(nvs, "pines", &pines, &largo) == ESP_OK) {
        destino = pines;
    }
}

Config cargar(nvs_handle_t nvs)
{
    Config config;
    leer_texto(nvs, "perfil", config.perfil);
    leer_texto(nvs, "wifi_ssid", config.wifi_ssid);
    leer_texto(nvs, "wifi_clave", config.wifi_clave);
    leer_texto(nvs, "servidor", config.servidor);
    leer_texto(nvs, "codigo", config.codigo);
    leer_texto(nvs, "token", config.token);
    leer_texto(nvs, "mqtt_url", config.mqtt_url);
    leer_texto(nvs, "mqtt_usuario", config.mqtt_usuario);
    leer_texto(nvs, "mqtt_clave", config.mqtt_clave);
    leer_pines(nvs, config.pines);
    leer_entero(nvs, "puerta_pin", config.puerta_pin);
    leer_entero(nvs, "puerta_s", config.puerta_segundos);
    leer_entero(nvs, "cara_min", config.cara_min);
    return config;
}

}  // namespace

esp_err_t config_iniciar()
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "La partición NVS cambió de formato: se borra y quedan los valores por defecto.");
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

    texto("perfil", nueva.perfil);
    texto("wifi_ssid", nueva.wifi_ssid);
    texto("wifi_clave", nueva.wifi_clave);
    texto("servidor", nueva.servidor);
    texto("codigo", nueva.codigo);
    texto("token", nueva.token);
    texto("mqtt_url", nueva.mqtt_url);
    texto("mqtt_usuario", nueva.mqtt_usuario);
    texto("mqtt_clave", nueva.mqtt_clave);
    if (err == ESP_OK) {
        err = nvs_set_blob(nvs, "pines", &nueva.pines, sizeof(PinesCamara));
    }
    entero("puerta_pin", nueva.puerta_pin);
    entero("puerta_s", nueva.puerta_segundos);
    entero("cara_min", nueva.cara_min);
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

std::string texto_firmware(const std::string& perfil)
{
    const esp_app_desc_t* aplicacion = esp_app_get_description();
    return "tinyml-" + (perfil.empty() ? std::string("sin_perfil") : perfil) + "-" + aplicacion->version;
}

}  // namespace accesia
