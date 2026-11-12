/**
 * Nombre: camara.cpp
 * Descripción: Inicio de la cámara con esp32-camera según el perfil, captura en QVGA y JPEG del recorte en memoria.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/camara.hpp"

#include <cstdlib>
#include <cstring>
#include <utility>

#include "esp_heap_caps.h"
#include "esp_log.h"
#include "img_converters.h"

namespace accesia {
namespace {

constexpr const char* TAG = "camara";
constexpr int XCLK_HZ = 20000000;  // 20 MHz, el valor de los ejemplos de esp32-camera
constexpr std::size_t BYTES_POR_PIXEL = 2;  // RGB565

}  // namespace

esp_err_t camara_iniciar(const Perfil& perfil, const PinesCamara& pines)
{
    camera_config_t config = {};
    config.pin_pwdn = pines.pwdn;
    config.pin_reset = pines.reset;
    config.pin_xclk = pines.xclk;
    config.pin_sccb_sda = pines.siod;
    config.pin_sccb_scl = pines.sioc;
    config.pin_d7 = pines.d7;
    config.pin_d6 = pines.d6;
    config.pin_d5 = pines.d5;
    config.pin_d4 = pines.d4;
    config.pin_d3 = pines.d3;
    config.pin_d2 = pines.d2;
    config.pin_d1 = pines.d1;
    config.pin_d0 = pines.d0;
    config.pin_vsync = pines.vsync;
    config.pin_href = pines.href;
    config.pin_pclk = pines.pclk;
    config.xclk_freq_hz = XCLK_HZ;
    config.ledc_timer = LEDC_TIMER_0;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.pixel_format = PIXFORMAT_RGB565;  // ESP-DL detecta sobre los píxeles, sin descomprimir
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;  // no se usa en RGB565
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_LATEST;

    const esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        return err;
    }
    sensor_t* sensor = esp_camera_sensor_get();
    if (sensor != nullptr) {
        sensor->set_vflip(sensor, perfil.voltear ? 1 : 0);
        sensor->set_hmirror(sensor, perfil.espejo ? 1 : 0);
        ESP_LOGI(TAG, "Sensor de la cámara: PID 0x%04x", sensor->id.PID);
    }
    return ESP_OK;
}

camera_fb_t* camara_capturar()
{
    return esp_camera_fb_get();
}

void camara_devolver(camera_fb_t* cuadro)
{
    if (cuadro != nullptr) {
        esp_camera_fb_return(cuadro);
    }
}

JpegRecorte::~JpegRecorte()
{
    liberar();
}

JpegRecorte::JpegRecorte(JpegRecorte&& otro) noexcept
    : datos_(std::exchange(otro.datos_, nullptr)), bytes_(std::exchange(otro.bytes_, 0))
{
}

JpegRecorte& JpegRecorte::operator=(JpegRecorte&& otro) noexcept
{
    if (this != &otro) {
        liberar();
        datos_ = std::exchange(otro.datos_, nullptr);
        bytes_ = std::exchange(otro.bytes_, 0);
    }
    return *this;
}

void JpegRecorte::liberar()
{
    std::free(datos_);  // fmt2jpg reserva la salida con malloc
    datos_ = nullptr;
    bytes_ = 0;
}

esp_err_t codificar_recorte(const camera_fb_t& cuadro, const Recorte& recorte, JpegRecorte& jpeg)
{
    if (cuadro.format != PIXFORMAT_RGB565) {
        return ESP_ERR_NOT_SUPPORTED;
    }
    const int ancho = recorte.ancho();
    const int alto = recorte.alto();
    if (ancho <= 0 || alto <= 0 || recorte.x0 < 0 || recorte.y0 < 0 ||
        recorte.x1 > static_cast<int>(cuadro.width) || recorte.y1 > static_cast<int>(cuadro.height)) {
        return ESP_ERR_INVALID_ARG;
    }

    // Copia las filas del recorte a un búfer propio en la PSRAM.
    const std::size_t bytes_fila = static_cast<std::size_t>(ancho) * BYTES_POR_PIXEL;
    const std::size_t total = bytes_fila * static_cast<std::size_t>(alto);
    auto* pixeles = static_cast<uint8_t*>(heap_caps_malloc(total, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (pixeles == nullptr) {
        pixeles = static_cast<uint8_t*>(std::malloc(total));
    }
    if (pixeles == nullptr) {
        return ESP_ERR_NO_MEM;
    }
    for (int fila = 0; fila < alto; ++fila) {
        const std::size_t desde =
            (static_cast<std::size_t>(recorte.y0 + fila) * cuadro.width + static_cast<std::size_t>(recorte.x0)) *
            BYTES_POR_PIXEL;
        std::memcpy(pixeles + static_cast<std::size_t>(fila) * bytes_fila, cuadro.buf + desde, bytes_fila);
    }

    uint8_t* salida = nullptr;
    std::size_t largo = 0;
    const bool comprimido = fmt2jpg(pixeles, total, static_cast<uint16_t>(ancho), static_cast<uint16_t>(alto),
                                    PIXFORMAT_RGB565, CALIDAD_JPEG, &salida, &largo);
    heap_caps_free(pixeles);
    if (!comprimido) {
        return ESP_FAIL;
    }
    jpeg.liberar();
    jpeg.datos_ = salida;
    jpeg.bytes_ = largo;
    return ESP_OK;
}

}  // namespace accesia
