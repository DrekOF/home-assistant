/**
 * Nombre: consola.cpp
 * Descripción: Consola serial de la placa: los comandos de arquitectura.md, leídos por UART0 y, si la placa lo tiene, por el USB nativo.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.3
 *
 * La consola principal de ESP-IDF es UART0. En la XIAO ESP32-C6 la secundaria es el USB Serial/JTAG, que solo
 * envía texto: por eso los comandos los leen tareas propias, con el driver de UART y el de USB Serial/JTAG, y los
 * pasan a esp_console_run. La salida sigue por la consola de ESP-IDF y llega a los dos puertos. La ESP32-CAM no
 * tiene USB nativo: su consola es solo UART0, con el adaptador USB (D-24).
 *
 * El driver de USB Serial/JTAG solo se usa para leer: la consola secundaria escribe directo en el FIFO y solo lo
 * vacía con cada salto de línea, así que el eco y el indicador lo vacían a mano (enviar_ya).
 *
 * Los comandos propios de cada placa (cara_min en la ESP32-CAM; sensor y antena en el C6) los registra su
 * componente con consola_registrar.
 */

#include "accesia/consola.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

#include "sdkconfig.h"

#include "driver/uart.h"
#include "driver/uart_vfs.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#if CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG
#include "driver/usb_serial_jtag.h"
#include "hal/usb_serial_jtag_ll.h"
#endif

#include "accesia/config.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "consola";
constexpr const char* INDICADOR = "accesia> ";
constexpr size_t LARGO_LINEA = 256;
constexpr uint32_t PILA_LECTOR = 6144;
constexpr UBaseType_t PRIORIDAD_LECTOR = 2;

struct Comando {
    const char* uso;
    const char* ejemplo;
};

SemaphoreHandle_t mutex_comandos = nullptr;
std::vector<Comando> comandos;
std::vector<void (*)()> lineas_de_estado;
void (*antes_de_cambiar_codigo)() = nullptr;
bool (*gpio_utilizable)(int, std::string&) = nullptr;

/// Envía ya lo escrito por los dos puertos.
void enviar_ya()
{
    fflush(stdout);
#if CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG
    usb_serial_jtag_ll_txfifo_flush();
#endif
}

bool leer_entero(const char* texto, int& valor)
{
    char* fin = nullptr;
    const long numero = std::strtol(texto, &fin, 10);
    if (fin == texto || *fin != '\0' || numero < -1000000 || numero > 1000000) {
        return false;
    }
    valor = static_cast<int>(numero);
    return true;
}

bool guardar(const Config& config)
{
    if (config_guardar(config) != ESP_OK) {
        printf("No se pudo guardar en NVS.\n");
        return false;
    }
    return true;
}

int uso(const char* texto)
{
    printf("Uso: %s\n", texto);
    return 1;
}

/// Código de la cámara como en openapi.yaml y base-de-datos.sql: ^[a-z0-9-]{3,32}$ y distinto de «servidor».
bool codigo_valido(std::string_view codigo)
{
    if (codigo.size() < 3 || codigo.size() > 32 || codigo == "servidor") {
        return false;
    }
    for (const char c : codigo) {
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) {
            return false;
        }
    }
    return true;
}

// ---------------------------------------------------------------- comandos comunes

int cmd_estado(int, char**)
{
    const Config c = config_leer();
    printf("Wi-Fi:     %s, %s\n", c.wifi_ssid.c_str(), c.wifi_clave.empty() ? "sin clave" : "clave guardada");
    printf("Servidor:  %s\n", c.servidor.c_str());
    printf("Código:    %s\n", c.codigo.empty() ? "sin código" : c.codigo.c_str());
    printf("Token:     %s\n", c.token.empty() ? "sin token" : "guardado");
    printf("MQTT:      %s, usuario %s, %s\n", c.mqtt_url.c_str(), c.mqtt_usuario.c_str(),
           c.mqtt_clave.empty() ? "sin clave" : "clave guardada");
    if (c.puerta_pin == PIN_NINGUNO) {
        printf("Puerta:    sin LED ni relé, %d s\n", c.puerta_segundos);
    } else {
        printf("Puerta:    GPIO %d, %d s, enciende en %s\n", c.puerta_pin, c.puerta_segundos,
               c.puerta_activo_bajo ? "bajo" : "alto");
    }
    for (void (*escribir)() : lineas_de_estado) {
        escribir();
    }
    return 0;
}

int cmd_wifi(int argc, char** argv)
{
    if (argc != 3) {
        return uso("wifi <ssid> <clave>   (si el nombre tiene espacios, va entre comillas)");
    }
    const size_t largo_ssid = strlen(argv[1]);
    const size_t largo_clave = strlen(argv[2]);
    if (largo_ssid < 1 || largo_ssid > 32) {
        printf("El nombre de la red tiene de 1 a 32 bytes.\n");
        return 1;
    }
    if (largo_clave < 8 || largo_clave > 63) {
        printf("La clave del Wi-Fi tiene de 8 a 63 caracteres.\n");
        return 1;
    }
    Config c = config_leer();
    c.wifi_ssid = argv[1];
    c.wifi_clave = argv[2];
    if (!guardar(c)) {
        return 1;
    }
    printf("Wi-Fi guardado: %s. Se aplica al reiniciar.\n", c.wifi_ssid.c_str());
    return 0;
}

int cmd_servidor(int argc, char** argv)
{
    if (argc != 2) {
        return uso("servidor <url>   por ejemplo: servidor http://" ACCESIA_IP_DE_LA_PI ":8000");
    }
    const std::string_view url = argv[1];
    if (!(url.starts_with("http://") || url.starts_with("https://")) || url.size() > 200) {
        printf("La dirección empieza con http:// o https:// y tiene hasta 200 caracteres.\n");
        return 1;
    }
    Config c = config_leer();
    c.servidor = argv[1];
    if (!guardar(c)) {
        return 1;
    }
    printf("Servidor guardado: %s.\n", c.servidor.c_str());
    return 0;
}

int cmd_codigo(int argc, char** argv)
{
    if (argc != 2) {
        return uso("codigo <codigo>   por ejemplo: codigo entrada");
    }
    if (!codigo_valido(argv[1])) {
        printf("El código usa de 3 a 32 letras minúsculas, números o guiones, y no puede ser «servidor».\n");
        return 1;
    }
    Config c = config_leer();
    if (c.codigo == argv[1]) {
        printf("El código ya es %s.\n", argv[1]);
        return 0;
    }
    if (!c.codigo.empty() && antes_de_cambiar_codigo != nullptr) {
        antes_de_cambiar_codigo();
    }
    c.codigo = argv[1];
    if (!guardar(c)) {
        return 1;
    }
    printf("Código guardado: %s. Se aplica al reiniciar (comando reiniciar).\n", c.codigo.c_str());
    return 0;
}

int cmd_token(int argc, char** argv)
{
    if (argc != 2) {
        return uso("token <token>   el que da la web al crear la cámara");
    }
    const size_t largo = strlen(argv[1]);
    if (largo < 1 || largo > 200) {
        printf("El token tiene de 1 a 200 caracteres.\n");
        return 1;
    }
    Config c = config_leer();
    c.token = argv[1];
    if (!guardar(c)) {
        return 1;
    }
    printf("Token guardado.\n");
    return 0;
}

int cmd_mqtt(int argc, char** argv)
{
    if (argc != 4) {
        return uso("mqtt <url> <usuario> <clave>   por ejemplo: mqtt mqtt://" ACCESIA_IP_DE_LA_PI
                   ":1883 camara clave123");
    }
    const std::string_view url = argv[1];
    if (!(url.starts_with("mqtt://") || url.starts_with("mqtts://")) || url.size() > 200) {
        printf("La dirección empieza con mqtt:// o mqtts:// y tiene hasta 200 caracteres.\n");
        return 1;
    }
    const size_t largo_usuario = strlen(argv[2]);
    const size_t largo_clave = strlen(argv[3]);
    if (largo_usuario < 1 || largo_usuario > 64 || largo_clave < 1 || largo_clave > 128) {
        printf("El usuario tiene de 1 a 64 caracteres y la clave, de 1 a 128.\n");
        return 1;
    }
    Config c = config_leer();
    c.mqtt_url = argv[1];
    c.mqtt_usuario = argv[2];
    c.mqtt_clave = argv[3];
    if (!guardar(c)) {
        return 1;
    }
    printf("MQTT guardado: %s, usuario %s. Se aplica al reiniciar.\n", c.mqtt_url.c_str(), c.mqtt_usuario.c_str());
    return 0;
}

int cmd_puerta(int argc, char** argv)
{
    if (argc != 3 && argc != 4) {
        return uso("puerta <pin> <segundos> [bajo|alto]   -1 si no hay LED ni relé; por ejemplo: puerta 15 3 bajo");
    }
    int gpio = 0;
    int segundos = 0;
    if (!leer_entero(argv[1], gpio) || !leer_entero(argv[2], segundos)) {
        printf("El pin y los segundos son enteros.\n");
        return 1;
    }
    if (gpio != PIN_NINGUNO) {
        std::string motivo;
        if (gpio < 0 || (gpio_utilizable != nullptr && !gpio_utilizable(gpio, motivo))) {
            printf("No sirve: %s.\n", motivo.empty() ? "el pin va desde 0, o -1 sin salida" : motivo.c_str());
            return 1;
        }
    }
    if (segundos < 1 || segundos > 60) {
        printf("La puerta queda abierta de 1 a 60 s.\n");
        return 1;
    }
    Config c = config_leer();
    if (argc == 4) {
        const std::string_view nivel = argv[3];
        if (nivel != "bajo" && nivel != "alto") {
            printf("El nivel que enciende es bajo o alto.\n");
            return 1;
        }
        c.puerta_activo_bajo = nivel == "bajo";
    }
    c.puerta_pin = gpio;
    c.puerta_segundos = segundos;
    if (!guardar(c)) {
        return 1;
    }
    printf("Puerta guardada: GPIO %d, %d s, enciende en %s. Se aplica al reiniciar.\n", gpio, segundos,
           c.puerta_activo_bajo ? "bajo" : "alto");
    return 0;
}

int cmd_reiniciar(int, char**)
{
    printf("Reiniciando...\n");
    enviar_ya();
    vTaskDelay(pdMS_TO_TICKS(200));
    esp_restart();
    return 0;
}

int cmd_ayuda(int, char**)
{
    printf("Comandos (se guardan en la placa y no hace falta recompilar):\n");
    for (const Comando& comando : comandos) {
        printf("  %-38s %s\n", comando.uso, comando.ejemplo);
    }
    return 0;
}

// ---------------------------------------------------------------- lectura de líneas

using FuncionLeer = int (*)(uint8_t* destino, size_t maximo);

struct Lector {
    const char* nombre;
    FuncionLeer leer;
};

#if CONFIG_ESP_CONSOLE_UART
// En C++ el número de la UART de la consola (un entero de sdkconfig) se pasa con el tipo del driver.
constexpr uart_port_t PUERTO_UART = static_cast<uart_port_t>(CONFIG_ESP_CONSOLE_UART_NUM);

int leer_uart(uint8_t* destino, size_t maximo)
{
    // uart_read_bytes espera hasta llenar el búfer o hasta el tiempo dado: con 20 ms responde a cada tecla.
    return uart_read_bytes(PUERTO_UART, destino, maximo, pdMS_TO_TICKS(20));
}
const Lector LECTOR_UART{"consola_uart", leer_uart};
#endif

#if CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG
int leer_usb(uint8_t* destino, size_t maximo)
{
    // Devuelve en cuanto llega algo.
    return usb_serial_jtag_read_bytes(destino, maximo, portMAX_DELAY);
}
const Lector LECTOR_USB{"consola_usb", leer_usb};
#endif

void mostrar_indicador()
{
    printf("%s", INDICADOR);
    enviar_ya();
}

void ejecutar(const char* linea)
{
    // esp_console_run usa un búfer propio: un comando a la vez, venga del puerto que venga.
    xSemaphoreTake(mutex_comandos, portMAX_DELAY);
    int resultado = 0;
    const esp_err_t err = esp_console_run(linea, &resultado);
    if (err == ESP_ERR_NOT_FOUND) {
        printf("No conozco ese comando. Escribe «ayuda».\n");
    } else if (err != ESP_OK && err != ESP_ERR_INVALID_ARG) {
        printf("Error: %s\n", esp_err_to_name(err));
    }
    mostrar_indicador();
    xSemaphoreGive(mutex_comandos);
}

void tarea_lector(void* argumento)
{
    const Lector& lector = *static_cast<const Lector*>(argumento);
    char linea[LARGO_LINEA];
    size_t largo = 0;
    int escape = 0;  // 0: normal; 1: llegó ESC; 2: dentro de una secuencia ESC [ (flechas y otras teclas)
    bool anterior_cr = false;
    uint8_t entrada[64];

    for (;;) {
        const int leidos = lector.leer(entrada, sizeof(entrada));
        for (int i = 0; i < leidos; ++i) {
            const char c = static_cast<char>(entrada[i]);
            const bool era_cr = anterior_cr;
            anterior_cr = (c == '\r');

            if (escape == 1) {
                escape = (c == '[') ? 2 : 0;
                continue;
            }
            if (escape == 2) {
                if (c >= 0x40 && c <= 0x7E) {
                    escape = 0;
                }
                continue;
            }
            if (c == 0x1B) {
                escape = 1;
                continue;
            }
            if (c == '\r' || c == '\n') {
                if (c == '\n' && era_cr) {
                    continue;  // \r\n es un solo Enter
                }
                printf("\n");
                linea[largo] = '\0';
                if (largo > 0) {
                    ejecutar(linea);
                } else {
                    mostrar_indicador();
                }
                largo = 0;
                continue;
            }
            if (c == '\b' || c == 0x7F) {
                if (largo > 0) {
                    // Borra un carácter completo, aunque ocupe varios bytes en UTF-8.
                    do {
                        --largo;
                    } while (largo > 0 && (static_cast<unsigned char>(linea[largo]) & 0xC0) == 0x80);
                    printf("\b \b");
                    enviar_ya();
                }
                continue;
            }
            if (static_cast<unsigned char>(c) < 0x20 || largo + 1 >= LARGO_LINEA) {
                continue;  // otros caracteres de control, o la línea ya está llena
            }
            linea[largo++] = c;
            putchar(c);
            enviar_ya();
        }
    }
}

esp_err_t arrancar_lector(const Lector& lector)
{
    const BaseType_t creada = xTaskCreate(tarea_lector, lector.nombre, PILA_LECTOR, const_cast<Lector*>(&lector),
                                          PRIORIDAD_LECTOR, nullptr);
    return creada == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}

}  // namespace

void consola_registrar(const char* comando, const char* uso, const char* ejemplo, esp_console_cmd_func_t funcion)
{
    // Los componentes registran con la consola ya andando: el mutex evita chocar con un comando en curso.
    xSemaphoreTake(mutex_comandos, portMAX_DELAY);
    esp_console_cmd_t cmd = {};
    cmd.command = comando;
    cmd.help = uso;
    cmd.func = funcion;
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd));
    comandos.push_back({uso, ejemplo});
    xSemaphoreGive(mutex_comandos);
}

void consola_agregar_estado(void (*escribir_lineas)())
{
    xSemaphoreTake(mutex_comandos, portMAX_DELAY);
    lineas_de_estado.push_back(escribir_lineas);
    xSemaphoreGive(mutex_comandos);
}

void consola_antes_de_cambiar_codigo(void (*antes)())
{
    antes_de_cambiar_codigo = antes;
}

void consola_revisar_gpio(bool (*utilizable)(int gpio, std::string& motivo))
{
    gpio_utilizable = utilizable;
}

esp_err_t consola_iniciar()
{
    mutex_comandos = xSemaphoreCreateMutex();
    ESP_RETURN_ON_FALSE(mutex_comandos != nullptr, ESP_ERR_NO_MEM, TAG, "Sin memoria para la consola");

    esp_console_config_t config = ESP_CONSOLE_CONFIG_DEFAULT();
    config.max_cmdline_length = LARGO_LINEA;
    config.max_cmdline_args = 8;
    ESP_RETURN_ON_ERROR(esp_console_init(&config), TAG, "No se pudo iniciar esp_console");

    consola_registrar("estado", "estado", "muestra la configuración y cómo está la placa", cmd_estado);
    consola_registrar("wifi", "wifi <ssid> <clave>", "wifi AccesIA clave123", cmd_wifi);
    consola_registrar("servidor", "servidor <url>", "servidor http://" ACCESIA_IP_DE_LA_PI ":8000", cmd_servidor);
    consola_registrar("codigo", "codigo <codigo>", "codigo entrada", cmd_codigo);
    consola_registrar("token", "token <token>", "el que da la web al crear la cámara", cmd_token);
    consola_registrar("mqtt", "mqtt <url> <usuario> <clave>",
                      "mqtt mqtt://" ACCESIA_IP_DE_LA_PI ":1883 camara clave123", cmd_mqtt);
    consola_registrar("puerta", "puerta <pin> <segundos> [bajo|alto]", "puerta 15 3 bajo; -1 sin LED ni relé",
                      cmd_puerta);
    consola_registrar("reiniciar", "reiniciar", "reinicia la placa", cmd_reiniciar);
    consola_registrar("ayuda", "ayuda", "esta lista", cmd_ayuda);
    fflush(stdout);

#if CONFIG_ESP_CONSOLE_UART
    // UART0: con el driver instalado, printf sale por él y los comandos se leen de su búfer.
    ESP_RETURN_ON_ERROR(uart_driver_install(PUERTO_UART, 1024, 0, 0, nullptr, 0), TAG,
                        "No se pudo instalar el driver de UART");
    uart_vfs_dev_use_driver(PUERTO_UART);
    ESP_RETURN_ON_ERROR(arrancar_lector(LECTOR_UART), TAG, "No se pudo crear la tarea de UART");
#endif

#if CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG
    // USB nativo: el driver solo lee; la salida sigue por la consola secundaria.
    usb_serial_jtag_driver_config_t usb = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(usb_serial_jtag_driver_install(&usb), TAG, "No se pudo instalar el driver de USB Serial/JTAG");
    ESP_RETURN_ON_ERROR(arrancar_lector(LECTOR_USB), TAG, "No se pudo crear la tarea de USB");
#endif

    printf("Escribe «ayuda» para ver los comandos.\n");
    mostrar_indicador();
    return ESP_OK;
}

}  // namespace accesia
