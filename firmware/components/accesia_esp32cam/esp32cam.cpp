/**
 * Nombre: esp32cam.cpp
 * Descripción: Ciclo de la ESP32-CAM (D-24): cuadro, modelo, presencia y recorte en una tarea, y el envío HTTP en otra; LED rojo y consola.
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * La tarea de visión (núcleo 1) no espera al servidor: le pasa el JPEG a la de envío (núcleo 0, junto al Wi-Fi)
 * por una cola de un lugar, y sigue detectando para que la presencia no se congele mientras llega la respuesta.
 * Ninguna imagen se guarda: el cuadro vuelve a la cámara y el JPEG se libera al enviarse (RNF-01).
 */

#include "accesia/esp32cam.hpp"

#include <atomic>
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <optional>

#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_psram.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "accesia/camara.hpp"
#include "accesia/consola.hpp"
#include "accesia/deteccion.hpp"
#include "accesia/envio.hpp"
#include "accesia/envio_logica.hpp"
#include "accesia/espera.hpp"
#include "accesia/mensajes.hpp"
#include "accesia/placa_esp32cam.hpp"
#include "accesia/presencia_logica.hpp"
#include "accesia/recorte.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "esp32cam";
constexpr const char* CLAVE_CARA_MIN = "cara_min";
constexpr int CARA_MIN_POR_DEFECTO = 80;  // CARA_MIN_PX del servidor (R7, api-dispositivo.md)
constexpr int PERIODO_LED_MS = 50;
constexpr uint32_t PILA_LED = 2048;
constexpr uint32_t PILA_VISION = 16384;
constexpr uint32_t PILA_ENVIO = 6144;
constexpr UBaseType_t PRIORIDAD_VISION = 3;
constexpr UBaseType_t PRIORIDAD_ENVIO = 4;
constexpr UBaseType_t PRIORIDAD_LED = 1;
constexpr BaseType_t NUCLEO_ENVIO = 0;   // el del Wi-Fi
constexpr BaseType_t NUCLEO_VISION = 1;  // el otro, para que la detección no frene la red
// ESP-DL 1.1 reserva sus búferes primero en la RAM interna y, si no alcanza, en la PSRAM: durante cada detección
// toma lo que haya libre. Por eso la memoria interna mínima se muestra en «estado» y cada minuto.
constexpr int64_t PERIODO_MEMORIA_MS = 60000;

/// Un recorte listo para enviar. La tarea de envío libera el JPEG.
struct Pedido {
    std::uint8_t* jpeg;
    std::size_t bytes;
    float puntaje;
};

Config config_actual;
std::string firmware;
std::string url;
EnlacesEsp32Cam enlaces_actuales;
QueueHandle_t cola_envio = nullptr;
TaskHandle_t manejo_vision = nullptr;
std::atomic<int> cara_min{CARA_MIN_POR_DEFECTO};

// Lo que comparten las tareas y la consola, con su cerrojo.
std::mutex cerrojo;
EsperaEntreRecortes espera;
PresenciaLogica presencia;
std::string error_camara;
int64_t ultima_deteccion_ms = -1;
uint32_t cuadros = 0;
uint32_t cuadros_fallidos = 0;
std::string ultimo_envio = "ninguno todavía";

int64_t ahora_ms()
{
    return esp_timer_get_time() / 1000;
}

unsigned kb_libres(uint32_t caps)
{
    return static_cast<unsigned>(heap_caps_get_free_size(caps) / 1024);
}

unsigned kb_minimos(uint32_t caps)
{
    return static_cast<unsigned>(heap_caps_get_minimum_free_size(caps) / 1024);
}

void registrar_memoria()
{
    ESP_LOGI(TAG, "Memoria: interna libre %u KB (mínimo %u KB, bloque mayor %u KB); PSRAM libre %u KB (mínimo %u KB)",
             kb_libres(MALLOC_CAP_INTERNAL), kb_minimos(MALLOC_CAP_INTERNAL),
             static_cast<unsigned>(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL) / 1024),
             kb_libres(MALLOC_CAP_SPIRAM), kb_minimos(MALLOC_CAP_SPIRAM));
}

bool puede_preparar_envio()
{
    if (config_actual.codigo.empty() || config_actual.token.empty()) {
        return false;
    }
    return enlaces_actuales.hay_red == nullptr || enlaces_actuales.hay_red();
}

/// Elige la cara, codifica su recorte y lo pasa a la tarea de envío. Se llama con el cuadro todavía prestado.
void preparar_envio(const vision::Cuadro& cuadro, const vision::Deteccion& deteccion, int64_t ahora)
{
    const std::optional<Eleccion> eleccion = elegir_recorte(deteccion.caras, cuadro.ancho, cuadro.alto, cara_min);
    if (!eleccion) {
        return;  // la cara más grande mide menos de cara_min, o no quedó recorte (RF-01 · C3)
    }
    JpegRecorte jpeg;
    if (codificar_recorte(cuadro, eleccion->recorte, jpeg) != ESP_OK) {
        ESP_LOGW(TAG, "No se pudo comprimir el recorte.");
        return;
    }
    if (jpeg.bytes() > JPEG_MAXIMO) {
        ESP_LOGW(TAG, "El JPEG del recorte pasa de 100 KB: no se envía (el servidor respondería 413).");
        return;
    }
    const float puntaje = eleccion->indice < deteccion.puntajes.size() ? deteccion.puntajes[eleccion->indice]
                                                                        : deteccion.puntaje;
    Pedido pedido{nullptr, jpeg.bytes(), puntaje};
    pedido.jpeg = jpeg.soltar();
    {
        std::lock_guard<std::mutex> bloqueo(cerrojo);
        espera.recorte_enviado();
    }
    if (xQueueSend(cola_envio, &pedido, 0) != pdTRUE) {
        std::free(pedido.jpeg);
        std::lock_guard<std::mutex> bloqueo(cerrojo);
        espera.esperar_desde(ahora, ESPERA_MINIMA_MS);
    }
}

[[noreturn]] void tarea_vision(void*)
{
    CamaraEsp32Cam camara;
    DetectorEspDl detector;
    bool avisado_sin_envio = false;
    int64_t proxima_memoria = ahora_ms() + PERIODO_MEMORIA_MS;

    for (;;) {
        if (ahora_ms() >= proxima_memoria) {
            registrar_memoria();
            proxima_memoria += PERIODO_MEMORIA_MS;
        }
        vision::Cuadro cuadro;
        if (!camara.capturar(cuadro)) {
            {
                std::lock_guard<std::mutex> bloqueo(cerrojo);
                ++cuadros_fallidos;
            }
            ESP_LOGW(TAG, "La cámara no entregó el cuadro; se intenta otra vez.");
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }

        const int64_t inicio_us = esp_timer_get_time();
        const vision::Deteccion deteccion = detector.detectar(cuadro);
        const int64_t fin_us = esp_timer_get_time();
        const int64_t ahora = fin_us / 1000;

        std::optional<std::string> por_publicar;
        bool puede_enviar = false;
        {
            std::lock_guard<std::mutex> bloqueo(cerrojo);
            ultima_deteccion_ms = (fin_us - inicio_us) / 1000;
            ++cuadros;
            if (presencia.cuadro(deteccion.hay_alguien, deteccion.puntaje, ahora)) {
                por_publicar = mensaje_presencia(presencia.presente(), presencia.puntaje());
            }
            puede_enviar = espera.puede_enviar(ahora);
        }
        if (por_publicar) {
            ESP_LOGI(TAG, "Presencia: %s", por_publicar->c_str());
            if (enlaces_actuales.publicar_presencia != nullptr) {
                enlaces_actuales.publicar_presencia(*por_publicar);
            }
        }

        if (deteccion.hay_alguien && puede_enviar) {
            if (puede_preparar_envio()) {
                preparar_envio(cuadro, deteccion, ahora);
            } else if (!avisado_sin_envio) {
                ESP_LOGW(TAG, "Hay una cara, pero sin código, sin token o sin Wi-Fi no se envía. Configúralos con "
                              "«codigo» y «token», y reinicia.");
                avisado_sin_envio = true;
            }
        }

        camara.devolver(cuadro);
        vTaskDelay(1);  // cede el núcleo un momento a las tareas de menor prioridad
    }
}

/// Lo que se muestra de una respuesta, como pide api-dispositivo.md («Qué hace la cámara con la respuesta»).
void mostrar_respuesta(const RespuestaEnvio& r, int64_t espera_ms)
{
    if (r.http == 200) {
        ESP_LOGI(TAG, "Servidor: %s · %s", r.resultado.c_str(), r.mensaje.c_str());
    } else if (r.http == 401 || r.http == 403) {
        ESP_LOGW(TAG, "El servidor no acepta esta cámara (%d, %s): revisa el código y el token. Reintento en 30 s.",
                 r.http, r.codigo_error.c_str());
    } else if (r.http == 429) {
        ESP_LOGW(TAG, "Demasiados recortes seguidos (429): espero %" PRId64 " s.", espera_ms / 1000);
    } else if (r.http == SIN_RESPUESTA) {
        ESP_LOGW(TAG, "Sin respuesta del servidor (%s): reintento en %" PRId64 " s.", r.error_red.c_str(),
                 espera_ms / 1000);
    } else {
        ESP_LOGW(TAG, "El servidor respondió %d (%s): %s. Reintento en %" PRId64 " s.", r.http, r.codigo_error.c_str(),
                 r.mensaje.c_str(), espera_ms / 1000);
    }
}

[[noreturn]] void tarea_envio(void*)
{
    int fallos_seguidos = 0;
    for (;;) {
        Pedido pedido{};
        if (xQueueReceive(cola_envio, &pedido, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        const RespuestaEnvio respuesta =
            envio_enviar(url, config_actual.token, firmware, pedido.jpeg, pedido.bytes, pedido.puntaje);
        std::free(pedido.jpeg);

        fallos_seguidos = es_fallo(respuesta.http) ? fallos_seguidos + 1 : 0;
        const int64_t espera_ms =
            espera_tras_envio(respuesta.http, respuesta.resultado, respuesta.reintentar_s, fallos_seguidos);
        {
            std::lock_guard<std::mutex> bloqueo(cerrojo);
            espera.esperar_desde(ahora_ms(), espera_ms);
            char texto[96];
            if (respuesta.http == 200) {
                std::snprintf(texto, sizeof(texto), "%s (%u bytes)", respuesta.resultado.c_str(),
                              static_cast<unsigned>(pedido.bytes));
            } else if (respuesta.http == SIN_RESPUESTA) {
                std::snprintf(texto, sizeof(texto), "sin respuesta (%s)", respuesta.error_red.c_str());
            } else {
                std::snprintf(texto, sizeof(texto), "HTTP %d %s", respuesta.http, respuesta.codigo_error.c_str());
            }
            ultimo_envio = texto;
        }
        mostrar_respuesta(respuesta, espera_ms);
    }
}

[[noreturn]] void tarea_led(void*)
{
    for (;;) {
        const bool puerta = enlaces_actuales.puerta_abierta_en_led != nullptr && enlaces_actuales.puerta_abierta_en_led();
        const Conexion conexion =
            enlaces_actuales.conexion != nullptr ? enlaces_actuales.conexion() : Conexion::conectada;
        const bool encendido = led_encendido(puerta, conexion, ahora_ms());
        gpio_set_level(static_cast<gpio_num_t>(PIN_LED_ROJO), encendido ? 0 : 1);  // enciende en bajo
        vTaskDelay(pdMS_TO_TICKS(PERIODO_LED_MS));
    }
}

int cmd_cara_min(int argc, char** argv)
{
    if (argc != 2) {
        printf("Uso: cara_min <px>   igual que CARA_MIN_PX del servidor (%d por defecto)\n", CARA_MIN_POR_DEFECTO);
        return 1;
    }
    char* fin = nullptr;
    const long px = std::strtol(argv[1], &fin, 10);
    if (fin == argv[1] || *fin != '\0' || px < 1 || px > ALTO_CUADRO) {
        printf("cara_min va de 1 a %d px, el alto del cuadro.\n", ALTO_CUADRO);
        return 1;
    }
    if (config_guardar_texto(CLAVE_CARA_MIN, std::to_string(px)) != ESP_OK) {
        printf("No se pudo guardar en NVS.\n");
        return 1;
    }
    cara_min = static_cast<int>(px);
    printf("cara_min = %ld px. Se aplica desde el siguiente cuadro.\n", px);
    return 0;
}

void escribir_estado()
{
    std::lock_guard<std::mutex> bloqueo(cerrojo);
    printf("Placa:     ESP32-CAM AI-Thinker, firmware %s\n", firmware.c_str());
    if (!error_camara.empty()) {
        printf("Cámara:    no arrancó (%s)\n", error_camara.c_str());
    } else {
        printf("Cámara:    PID 0x%02x, QVGA en RGB565; %" PRIu32 " cuadros, %" PRIu32 " fallidos\n",
               camara_sensor_pid(), cuadros, cuadros_fallidos);
    }
    if (ultima_deteccion_ms >= 0) {
        printf("Modelo:    ESP-DL 1.1, MSR01 + MNP01; la última detección tardó %" PRId64 " ms\n", ultima_deteccion_ms);
    } else {
        printf("Modelo:    ESP-DL 1.1, MSR01 + MNP01; sin detecciones todavía\n");
    }
    const std::optional<float> puntaje = presencia.puntaje();
    printf("Presencia: %s", presencia.presente() ? "hay alguien" : "nadie");
    if (puntaje) {
        printf(" (puntaje %s)", texto_puntaje(*puntaje).c_str());
    }
    printf("; vuelve a nadie tras %d s sin caras\n", static_cast<int>(PRESENCIA_SOSTENER_MS / 1000));
    printf("Envío:     %s; cara_min %d px\n", ultimo_envio.c_str(), cara_min.load());
    printf("Memoria:   interna libre %u KB (mínimo %u KB); PSRAM %d KB, libre %u KB (mínimo %u KB)\n",
           kb_libres(MALLOC_CAP_INTERNAL), kb_minimos(MALLOC_CAP_INTERNAL), esp32cam_psram_kb(),
           kb_libres(MALLOC_CAP_SPIRAM), kb_minimos(MALLOC_CAP_SPIRAM));
    if (manejo_vision != nullptr) {
        printf("Pila:      a la tarea de visión le sobran %u bytes de %u\n",
               static_cast<unsigned>(uxTaskGetStackHighWaterMark(manejo_vision)), static_cast<unsigned>(PILA_VISION));
    }
}

esp_err_t iniciar_led()
{
    const gpio_num_t led = static_cast<gpio_num_t>(PIN_LED_ROJO);
    ESP_RETURN_ON_ERROR(gpio_reset_pin(led), TAG, "GPIO del LED inválido");
    ESP_RETURN_ON_ERROR(gpio_set_direction(led, GPIO_MODE_OUTPUT), TAG, "El LED no quedó de salida");
    gpio_set_level(led, 1);  // apagado: enciende en bajo
    const BaseType_t creada = xTaskCreate(tarea_led, "led", PILA_LED, nullptr, PRIORIDAD_LED, nullptr);
    return creada == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}

}  // namespace

esp_err_t esp32cam_iniciar(const Config& config, const EnlacesEsp32Cam& enlaces)
{
    config_actual = config;
    enlaces_actuales = enlaces;
    firmware = texto_firmware(PERFIL_ESP32CAM);
    url = url_rostros(config.servidor, config.codigo);
    const int guardado = std::atoi(config_texto(CLAVE_CARA_MIN, "").c_str());
    cara_min = (guardado >= 1 && guardado <= ALTO_CUADRO) ? guardado : CARA_MIN_POR_DEFECTO;

    consola_registrar("cara_min", "cara_min <px>", "cara_min 80, igual que CARA_MIN_PX del servidor", cmd_cara_min);
    consola_agregar_estado(escribir_estado);
    consola_revisar_gpio(gpio_utilizable_esp32cam);
    ESP_RETURN_ON_ERROR(iniciar_led(), TAG, "No se pudo usar el LED rojo");

    const esp_err_t err = camara_iniciar();
    if (err != ESP_OK) {
        std::lock_guard<std::mutex> bloqueo(cerrojo);
        error_camara = esp_err_to_name(err);
        return err;
    }
    if (config.codigo.empty() || config.token.empty()) {
        ESP_LOGW(TAG, "Sin código o sin token: la cámara detecta y publica su presencia, pero no envía recortes. "
                      "Configúralos con «codigo» y «token», y reinicia.");
    }

    cola_envio = xQueueCreate(1, sizeof(Pedido));
    ESP_RETURN_ON_FALSE(cola_envio != nullptr, ESP_ERR_NO_MEM, TAG, "Sin memoria para la cola de envío");
    ESP_RETURN_ON_FALSE(xTaskCreatePinnedToCore(tarea_envio, "envio", PILA_ENVIO, nullptr, PRIORIDAD_ENVIO, nullptr,
                                                NUCLEO_ENVIO) == pdPASS,
                        ESP_ERR_NO_MEM, TAG, "No se pudo crear la tarea de envío");
    ESP_RETURN_ON_FALSE(xTaskCreatePinnedToCore(tarea_vision, "vision", PILA_VISION, nullptr, PRIORIDAD_VISION,
                                                &manejo_vision, NUCLEO_VISION) == pdPASS,
                        ESP_ERR_NO_MEM, TAG, "No se pudo crear la tarea de visión");
    ESP_LOGI(TAG, "Cámara lista: QVGA en RGB565, ESP-DL 1.1 (MSR01 + MNP01), cara_min %d px, envío a %s.",
             cara_min.load(), url.c_str());
    registrar_memoria();
    return ESP_OK;
}

std::string esp32cam_mensaje_presencia()
{
    std::lock_guard<std::mutex> bloqueo(cerrojo);
    return mensaje_presencia(presencia.presente(), presencia.puntaje());
}

int esp32cam_psram_kb()
{
    return esp_psram_is_initialized() ? static_cast<int>(esp_psram_get_size() / 1024) : 0;
}

}  // namespace accesia
