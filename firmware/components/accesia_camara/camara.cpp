/**
 * Nombre: camara.cpp
 * Descripción: Inicio de la OV2640 de la ESP32-CAM AI-Thinker con esp32-camera, captura en QVGA y JPEG del recorte en memoria (D-24).
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Viene del firmware del ESP32-S3 (PR #7), con los pines fijos de la AI-Thinker en vez de los perfiles.
 */

#include "accesia/camara.hpp"

#include <cstdlib>
#include <cstring>

#include "driver/gpio.h"
#include "esp_camera.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "img_converters.h"

#include "accesia/placa_esp32cam.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "camara";
constexpr int XCLK_HZ = 20000000;  // 20 MHz, el valor de los ejemplos de esp32-camera
constexpr std::size_t BYTES_POR_PIXEL = 2;  // RGB565

int pid_sensor = 0;

}  // namespace

esp_err_t camara_iniciar()
{
    // El LED blanco del flash (GPIO4) queda apagado: con el pin flotando puede encenderse tenue.
    gpio_reset_pin(static_cast<gpio_num_t>(PIN_LED_FLASH));
    gpio_set_direction(static_cast<gpio_num_t>(PIN_LED_FLASH), GPIO_MODE_OUTPUT);
    gpio_set_level(static_cast<gpio_num_t>(PIN_LED_FLASH), 0);

    const PinesCamaraEsp32Cam& p = PINES_CAMARA_ESP32CAM;
    camera_config_t config = {};
    config.pin_pwdn = p.pwdn;
    config.pin_reset = p.reset;
    config.pin_xclk = p.xclk;
    config.pin_sccb_sda = p.siod;
    config.pin_sccb_scl = p.sioc;
    config.pin_d7 = p.d7;
    config.pin_d6 = p.d6;
    config.pin_d5 = p.d5;
    config.pin_d4 = p.d4;
    config.pin_d3 = p.d3;
    config.pin_d2 = p.d2;
    config.pin_d1 = p.d1;
    config.pin_d0 = p.d0;
    config.pin_vsync = p.vsync;
    config.pin_href = p.href;
    config.pin_pclk = p.pclk;
    config.xclk_freq_hz = XCLK_HZ;
    config.ledc_timer = LEDC_TIMER_0;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.pixel_format = PIXFORMAT_RGB565;  // ESP-DL detecta sobre los píxeles, sin descomprimir
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;  // no se usa en RGB565
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_LATEST;

    ESP_RETURN_ON_ERROR(esp_camera_init(&config), TAG, "No arrancó la cámara");
    sensor_t* sensor = esp_camera_sensor_get();
    if (sensor != nullptr) {
        pid_sensor = sensor->id.PID;
        ESP_LOGI(TAG, "Sensor de la cámara: PID 0x%04x (la OV2640 es 0x26).", pid_sensor);
    }
    return ESP_OK;
}

int camara_sensor_pid()
{
    return pid_sensor;
}

bool CamaraEsp32Cam::capturar(vision::Cuadro& cuadro)
{
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb == nullptr) {
        return false;
    }
    actual_ = fb;
    cuadro.datos = fb->buf;
    cuadro.bytes = fb->len;
    cuadro.ancho = static_cast<std::uint16_t>(fb->width);
    cuadro.alto = static_cast<std::uint16_t>(fb->height);
    cuadro.jpeg = fb->format == PIXFORMAT_JPEG;
    return true;
}

void CamaraEsp32Cam::devolver(vision::Cuadro& cuadro)
{
    if (actual_ != nullptr) {
        esp_camera_fb_return(static_cast<camera_fb_t*>(actual_));
        actual_ = nullptr;
    }
    cuadro = vision::Cuadro{};
}

JpegRecorte::~JpegRecorte()
{
    std::free(datos_);  // fmt2jpg reserva la salida con malloc
}

std::uint8_t* JpegRecorte::soltar()
{
    std::uint8_t* datos = datos_;
    datos_ = nullptr;
    bytes_ = 0;
    return datos;
}

esp_err_t codificar_recorte(const vision::Cuadro& cuadro, const Recorte& recorte, JpegRecorte& jpeg)
{
    if (cuadro.jpeg || cuadro.datos == nullptr) {
        return ESP_ERR_NOT_SUPPORTED;
    }
    const int ancho = recorte.ancho();
    const int alto = recorte.alto();
    if (ancho <= 0 || alto <= 0 || recorte.x0 < 0 || recorte.y0 < 0 || recorte.x1 > cuadro.ancho ||
        recorte.y1 > cuadro.alto) {
        return ESP_ERR_INVALID_ARG;
    }

    // Copia las filas del recorte a un búfer propio en la PSRAM.
    const std::size_t bytes_fila = static_cast<std::size_t>(ancho) * BYTES_POR_PIXEL;
    const std::size_t total = bytes_fila * static_cast<std::size_t>(alto);
    auto* pixeles = static_cast<std::uint8_t*>(heap_caps_malloc(total, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (pixeles == nullptr) {
        return ESP_ERR_NO_MEM;
    }
    for (int fila = 0; fila < alto; ++fila) {
        const std::size_t desde =
            (static_cast<std::size_t>(recorte.y0 + fila) * cuadro.ancho + static_cast<std::size_t>(recorte.x0)) *
            BYTES_POR_PIXEL;
        std::memcpy(pixeles + static_cast<std::size_t>(fila) * bytes_fila, cuadro.datos + desde, bytes_fila);
    }

    std::uint8_t* salida = nullptr;
    std::size_t largo = 0;
    const bool comprimido = fmt2jpg(pixeles, total, static_cast<uint16_t>(ancho), static_cast<uint16_t>(alto),
                                    PIXFORMAT_RGB565, CALIDAD_JPEG, &salida, &largo);
    heap_caps_free(pixeles);
    if (!comprimido) {
        return ESP_FAIL;
    }
    std::free(jpeg.datos_);
    jpeg.datos_ = salida;
    jpeg.bytes_ = largo;
    return ESP_OK;
}

}  // namespace accesia
