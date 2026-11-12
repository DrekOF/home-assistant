/**
 * Nombre: main.cpp
 * Descripción: Arranque de la cámara: configuración, consola, cámara según el perfil y bucle de detección (Día 1, sin envío).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * Por ahora muestra por el monitor serial cada cara (caja y puntaje) y el recorte que enviaría (píxeles y bytes).
 * El envío por HTTP y la puerta por MQTT llegan el Día 3. Ninguna imagen se guarda: el cuadro vuelve a la cámara
 * y el JPEG del recorte se libera en la misma vuelta del bucle (RNF-01).
 */

#include <cinttypes>
#include <cstdio>
#include <string>
#include <vector>

#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "accesia/camara.hpp"
#include "accesia/config.hpp"
#include "accesia/consola.hpp"
#include "accesia/deteccion.hpp"
#include "accesia/espera.hpp"
#include "accesia/perfiles.hpp"
#include "accesia/recorte.hpp"

namespace {

constexpr const char* TAG = "accesia";

void mostrar_inicio(const accesia::Config& config)
{
    const accesia::TipoPsram psram = accesia::psram_del_binario();
    printf("\nAccesIA · cámara %s · binario %s\n", accesia::texto_firmware(config.perfil).c_str(),
           accesia::nombre_psram(psram));
    printf("Perfiles de este binario:");
    for (const accesia::Perfil& perfil : accesia::perfiles()) {
        if (perfil.psram == psram) {
            printf(" %s", perfil.nombre);
        }
    }
    printf("\n");
}

/// Perfil con sus pines listos para la cámara, o nullptr si falta algo (y lo explica por el monitor serial).
const accesia::Perfil* perfil_listo(const accesia::Config& config, accesia::PinesCamara& pines)
{
    if (config.perfil.empty()) {
        ESP_LOGW(TAG, "Sin perfil: la cámara no se inicia. Elige uno con «perfil <nombre>» y reinicia.");
        return nullptr;
    }
    const accesia::Perfil* perfil = accesia::buscar_perfil(config.perfil);
    if (perfil == nullptr) {
        ESP_LOGW(TAG, "El perfil %s no es de este binario (%s). Elige otro con «perfil».", config.perfil.c_str(),
                 accesia::nombre_psram(accesia::psram_del_binario()));
        return nullptr;
    }
    pines = perfil->generico ? config.pines : perfil->pines;
    std::string motivo;
    if (!accesia::revisar_pines(pines, motivo)) {
        ESP_LOGW(TAG, "Pines del perfil %s: %s. Corrígelos con «pin <nombre> <número>» y reinicia.", perfil->nombre,
                 motivo.c_str());
        return nullptr;
    }
    return perfil;
}

/// Muestra el recorte que se enviaría: la cara elegida, su tamaño y los bytes del JPEG. El JPEG se libera al salir.
void mostrar_recorte(const camera_fb_t& cuadro, const accesia::Eleccion& eleccion)
{
    const accesia::Recorte& r = eleccion.recorte;
    accesia::JpegRecorte jpeg;
    if (accesia::codificar_recorte(cuadro, r, jpeg) != ESP_OK) {
        ESP_LOGW(TAG, "No se pudo comprimir el recorte.");
        return;
    }
    ESP_LOGI(TAG, "Recorte que enviaría: cara %u, de (%d, %d) a (%d, %d), %d × %d px, %u bytes de JPEG",
             static_cast<unsigned>(eleccion.indice), r.x0, r.y0, r.x1, r.y1, r.ancho(), r.alto(),
             static_cast<unsigned>(jpeg.bytes()));
    if (jpeg.bytes() > accesia::JPEG_MAXIMO) {
        ESP_LOGW(TAG, "El JPEG pasa de 100 KB: el servidor lo rechazaría (413).");
    }
}

[[noreturn]] void detectar_sin_enviar(accesia::Detector& detector)
{
    for (;;) {
        camera_fb_t* cuadro = accesia::camara_capturar();
        if (cuadro == nullptr) {
            ESP_LOGW(TAG, "La cámara no entregó el cuadro; se intenta otra vez.");
            vTaskDelay(pdMS_TO_TICKS(accesia::ESPERA_MINIMA_MS));
            continue;
        }

        const int64_t inicio = esp_timer_get_time();
        const std::vector<accesia::CaraDetectada> caras = detector.detectar(*cuadro);
        const int64_t milisegundos = (esp_timer_get_time() - inicio) / 1000;

        if (!caras.empty()) {
            std::vector<accesia::Caja> cajas;
            for (size_t i = 0; i < caras.size(); ++i) {
                const accesia::Caja& caja = caras[i].caja;
                ESP_LOGI(TAG, "Cara %u: caja (%d, %d, %d, %d), puntaje %.2f", static_cast<unsigned>(i), caja.x, caja.y,
                         caja.w, caja.h, static_cast<double>(caras[i].puntaje));
                cajas.push_back(caja);
            }
            const int cara_min = accesia::config_leer().cara_min;
            const auto eleccion = accesia::elegir_recorte(cajas, cuadro->width, cuadro->height, cara_min);
            if (eleccion) {
                mostrar_recorte(*cuadro, *eleccion);
            } else {
                ESP_LOGI(TAG, "No se enviaría nada: la cara más grande mide menos de %d px de alto (cara_min).",
                         cara_min);
            }
            ESP_LOGI(TAG, "Detección en %" PRId64 " ms", milisegundos);
        }

        accesia::camara_devolver(cuadro);
        // Día 1, sin envío: un cuadro por segundo, la espera mínima entre recortes.
        vTaskDelay(pdMS_TO_TICKS(accesia::ESPERA_MINIMA_MS));
    }
}

}  // namespace

extern "C" void app_main(void)
{
    ESP_ERROR_CHECK(accesia::config_iniciar());
    const accesia::Config config = accesia::config_leer();
    mostrar_inicio(config);
    ESP_ERROR_CHECK(accesia::consola_iniciar());

    accesia::PinesCamara pines;
    const accesia::Perfil* perfil = perfil_listo(config, pines);
    if (perfil == nullptr) {
        return;  // la consola sigue atendiendo para elegir el perfil o los pines
    }

    const esp_err_t err = accesia::camara_iniciar(*perfil, pines);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo iniciar la cámara con el perfil %s: %s. Revisa el perfil y los pines.",
                 perfil->nombre, esp_err_to_name(err));
        return;
    }
    ESP_LOGI(TAG, "Cámara lista con el perfil %s (%s), en QVGA y RGB565.", perfil->nombre, perfil->placa);

    accesia::Detector detector;
    detectar_sin_enviar(detector);
}
