/**
 * Nombre: main.cpp
 * Descripción: Arranque de la placa: configuración, consola, puerta, Wi-Fi y MQTT, y lo de cada target: la cámara y su modelo en la ESP32-CAM (D-24); la antena, el sensor y el LED en la XIAO ESP32-C6 (D-21).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.1
 *
 * En la ESP32-CAM, la placa detecta caras con ESP-DL 1.1, envía el recorte al servidor, publica su presencia y
 * abre la puerta con el LED rojo. El Wi-Fi y MQTT arrancan antes que la cámara y el modelo, porque ESP-DL toma en
 * cada detección la RAM interna que quede libre.
 */

#include <cstdio>
#include <string>

#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "sdkconfig.h"

#include "accesia/config.hpp"
#include "accesia/consola.hpp"
#include "accesia/led.hpp"
#include "accesia/mensajes.hpp"
#include "accesia/mqtt.hpp"
#include "accesia/puerta.hpp"
#include "accesia/red.hpp"

#if CONFIG_IDF_TARGET_ESP32
#include "accesia/esp32cam.hpp"
#include "accesia/placa_esp32cam.hpp"
#elif CONFIG_IDF_TARGET_ESP32C6
#include "accesia/ambiente.hpp"
#include "accesia/placa.hpp"
#endif

namespace {

constexpr const char* TAG = "accesia";

#if CONFIG_IDF_TARGET_ESP32
constexpr const char* PERFIL = accesia::PERFIL_ESP32CAM;
constexpr int PIN_LED_COMPARTIDO = accesia::PIN_LED_ROJO;  // la puerta de fábrica es el LED rojo
#elif CONFIG_IDF_TARGET_ESP32C6
constexpr const char* PERFIL = accesia::PERFIL_C6;
constexpr int PIN_LED_COMPARTIDO = accesia::PIN_LED;  // la puerta de fábrica es el LED de estado
#else
constexpr const char* PERFIL = "sin_perfil";
constexpr int PIN_LED_COMPARTIDO = accesia::PIN_NINGUNO;
#endif

/// Sigue arrancando aunque falle una parte, para que la consola quede disponible y diga qué pasó.
void revisar(esp_err_t err, const char* que)
{
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo iniciar %s: %s", que, esp_err_to_name(err));
    }
}

/// El mensaje EstadoCamara (mqtt.md), cada 60 s y al conectarse al broker.
std::string armar_estado()
{
    accesia::EstadoPlaca estado;
    estado.perfil = PERFIL;
    estado.firmware = accesia::texto_firmware(PERFIL);
    estado.ip = accesia::red_ip();
    estado.rssi = accesia::red_rssi();
    estado.libre_kb = static_cast<int>(esp_get_free_heap_size() / 1024);
#if CONFIG_IDF_TARGET_ESP32
    estado.psram_kb = accesia::esp32cam_psram_kb();
#elif CONFIG_IDF_TARGET_ESP32C6
    estado.sensor = accesia::nombre_sensor(accesia::ambiente_tipo());
    estado.antena = accesia::nombre_antena(accesia::placa_antena());
#endif
    estado.segundos_encendida = esp_timer_get_time() / 1000000;
    return accesia::mensaje_estado(estado);
}

/// Para el parpadeo del LED: lento sin Wi-Fi, rápido sin broker y apagado con todo conectado.
[[maybe_unused]] accesia::Conexion conexion()
{
    if (!accesia::red_conectada()) {
        return accesia::Conexion::sin_wifi;
    }
    return accesia::mqtt_conectado() ? accesia::Conexion::conectada : accesia::Conexion::sin_broker;
}

}  // namespace

extern "C" void app_main(void)
{
    ESP_ERROR_CHECK(accesia::config_iniciar());
#if CONFIG_IDF_TARGET_ESP32C6
    // La antena va antes del Wi-Fi: ESP-IDF no enciende solo el conmutador de la XIAO.
    revisar(accesia::placa_elegir_antena(), "la antena");
#endif
    const accesia::Config config = accesia::config_leer();
    printf("\nAccesIA · placa %s\n", accesia::texto_firmware(PERFIL).c_str());
    ESP_ERROR_CHECK(accesia::consola_iniciar());

    revisar(accesia::puerta_iniciar(config, PIN_LED_COMPARTIDO), "la puerta");
    accesia::puerta_al_cambiar(accesia::mqtt_publicar_puerta);
    accesia::consola_antes_de_cambiar_codigo(accesia::mqtt_borrar_descubrimiento);

    revisar(accesia::red_iniciar(config), "el Wi-Fi");

    accesia::EnlacesMqtt enlaces;
    enlaces.al_recibir_puerta = accesia::puerta_orden;
    enlaces.puerta_abierta = accesia::puerta_abierta;
    enlaces.armar_estado = armar_estado;
#if CONFIG_IDF_TARGET_ESP32
    enlaces.publica_presencia = true;
    enlaces.armar_presencia = accesia::esp32cam_mensaje_presencia;
#elif CONFIG_IDF_TARGET_ESP32C6
    enlaces.publica_ambiente = true;
#endif
    revisar(accesia::mqtt_iniciar(config, enlaces), "MQTT");

#if CONFIG_IDF_TARGET_ESP32
    accesia::EnlacesEsp32Cam camara;
    camara.publicar_presencia = accesia::mqtt_publicar_presencia;
    camara.puerta_abierta_en_led = accesia::puerta_abierta_en_led;
    camara.conexion = conexion;
    camara.hay_red = accesia::red_conectada;
    revisar(accesia::esp32cam_iniciar(config, camara), "la cámara");
#elif CONFIG_IDF_TARGET_ESP32C6
    revisar(accesia::ambiente_iniciar(accesia::mqtt_publicar_ambiente), "el sensor");
    revisar(accesia::placa_iniciar(accesia::puerta_abierta_en_led, conexion), "el LED");
#endif
    ESP_LOGI(TAG, "Placa lista. Escribe «estado» para ver cómo está.");
}
