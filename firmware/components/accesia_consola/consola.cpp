/**
 * Nombre: consola.cpp
 * Descripción: Consola serial de la cámara: los comandos de arquitectura.md, leídos por UART0 y por el USB nativo a la vez.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 *
 * La consola principal de ESP-IDF es UART0 y la secundaria, el USB Serial/JTAG, que solo envía texto. Por eso
 * los comandos los leen dos tareas propias, con el driver de UART y el de USB Serial/JTAG, y los pasan a
 * esp_console_run. La salida sigue por la consola de ESP-IDF y llega a los dos puertos.
 *
 * El driver de USB Serial/JTAG solo se usa para leer: la consola secundaria escribe directo en el FIFO y solo lo
 * vacía con cada salto de línea, así que el eco y el indicador lo vacían a mano (enviar_ya).
 */

#include "accesia/consola.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <string_view>

#include "driver/uart.h"
#include "driver/uart_vfs.h"
#include "driver/usb_serial_jtag.h"
#include "esp_check.h"
#include "esp_console.h"
#include "esp_log.h"
#include "esp_psram.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "hal/usb_serial_jtag_ll.h"
#include "sdkconfig.h"

#include "accesia/config.hpp"
#include "accesia/perfiles.hpp"

namespace accesia {
namespace {

constexpr const char* TAG = "consola";
constexpr const char* INDICADOR = "accesia> ";
constexpr size_t LARGO_LINEA = 256;
constexpr uint32_t PILA_LECTOR = 6144;
constexpr UBaseType_t PRIORIDAD_LECTOR = 2;  // por encima del bucle de detección, para que escribir no se trabe

SemaphoreHandle_t mutex_comandos = nullptr;

/// Envía ya lo escrito por los dos puertos.
void enviar_ya()
{
    fflush(stdout);
    usb_serial_jtag_ll_txfifo_flush();
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

void mostrar_pines(const PinesCamara& pines)
{
    printf("Pines:    ");
    for (size_t i = 0; i < CANTIDAD_PINES; ++i) {
        printf(" %s %d", NOMBRES_PINES[i], valor_pin(pines, i));
    }
    printf("\n");
}

// ---------------------------------------------------------------- comandos

int cmd_estado(int, char**)
{
    const Config c = config_leer();
    const Perfil* perfil = buscar_perfil(c.perfil);
    const char* psram = nombre_psram(psram_del_binario());

    printf("Firmware:  %s (binario %s)\n", texto_firmware(c.perfil).c_str(), psram);
    if (perfil != nullptr) {
        printf("Perfil:    %s, %s\n", perfil->nombre, perfil->placa);
    } else if (c.perfil.empty()) {
        printf("Perfil:    sin elegir (usa «perfil <nombre>»)\n");
    } else {
        printf("Perfil:    %s no es de este binario\n", c.perfil.c_str());
    }
    printf("Wi-Fi:     %s, %s\n", c.wifi_ssid.c_str(), c.wifi_clave.empty() ? "sin clave" : "clave guardada");
    printf("IP:        sin conexión\n");
    printf("Servidor:  %s\n", c.servidor.c_str());
    printf("Código:    %s\n", c.codigo.empty() ? "sin código" : c.codigo.c_str());
    printf("Token:     %s\n", c.token.empty() ? "sin token" : "guardado");
    printf("MQTT:      %s, usuario %s, %s\n", c.mqtt_url.c_str(), c.mqtt_usuario.c_str(),
           c.mqtt_clave.empty() ? "sin clave" : "clave guardada");
    printf("PSRAM:     %u KB (%s)\n", static_cast<unsigned>(esp_psram_get_size() / 1024), psram);
    printf("cara_min:  %d px\n", c.cara_min);
    if (c.puerta_pin == SIN_PIN) {
        printf("Puerta:    sin LED ni relé, %d s\n", c.puerta_segundos);
    } else {
        printf("Puerta:    GPIO %d, %d s\n", c.puerta_pin, c.puerta_segundos);
    }
    if (perfil != nullptr && perfil->generico) {
        mostrar_pines(c.pines);
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
    printf("Wi-Fi guardado: %s.\n", c.wifi_ssid.c_str());
    return 0;
}

int cmd_servidor(int argc, char** argv)
{
    if (argc != 2) {
        return uso("servidor <url>   por ejemplo: servidor http://10.42.0.1:8000");
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
    c.codigo = argv[1];
    if (!guardar(c)) {
        return 1;
    }
    printf("Código guardado: %s.\n", c.codigo.c_str());
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
        return uso("mqtt <url> <usuario> <clave>   por ejemplo: mqtt mqtt://10.42.0.1:1883 camara clave123");
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
    printf("MQTT guardado: %s, usuario %s.\n", c.mqtt_url.c_str(), c.mqtt_usuario.c_str());
    return 0;
}

int cmd_perfil(int argc, char** argv)
{
    const Config actual = config_leer();
    const TipoPsram psram = psram_del_binario();
    if (argc == 1) {
        printf("Perfiles de este binario (%s); el marcado con * es el elegido:\n", nombre_psram(psram));
        for (const Perfil& p : perfiles()) {
            if (p.psram == psram) {
                printf("  %s %-16s %s\n", actual.perfil == p.nombre ? "*" : " ", p.nombre, p.placa);
            }
        }
        return 0;
    }
    if (argc != 2) {
        return uso("perfil [nombre]   sin nombre, lista los perfiles de este binario");
    }
    const Perfil* perfil = buscar_perfil(argv[1]);
    if (perfil == nullptr) {
        for (const Perfil& p : perfiles()) {
            if (std::string_view(argv[1]) == p.nombre) {
                printf("%s es del binario %s y este es el binario %s.\n", p.nombre, nombre_psram(p.psram),
                       nombre_psram(psram));
                return 1;
            }
        }
        printf("No conozco ese perfil. Escribe «perfil» para ver los de este binario.\n");
        return 1;
    }
    Config c = actual;
    c.perfil = perfil->nombre;
    if (!guardar(c)) {
        return 1;
    }
    printf("Perfil guardado: %s. Se usa al reiniciar (comando reiniciar).\n", perfil->nombre);
    if (perfil->generico) {
        printf("Es genérico: define sus pines con «pin <nombre> <número>» antes de reiniciar.\n");
    }
    return 0;
}

int cmd_pin(int argc, char** argv)
{
    if (argc != 3) {
        return uso("pin <nombre> <número>   nombres: pwdn reset xclk siod sioc d0 a d7 vsync href pclk");
    }
    Config c = config_leer();
    const Perfil* perfil = buscar_perfil(c.perfil);
    if (perfil == nullptr || !perfil->generico) {
        printf("Los pines solo se cambian en los perfiles genéricos (generico_octal o generico_quad).\n");
        return 1;
    }
    int* campo = pin_por_nombre(c.pines, argv[1]);
    if (campo == nullptr) {
        printf("No conozco el pin %s.\n", argv[1]);
        return 1;
    }
    int gpio = 0;
    if (!leer_entero(argv[2], gpio)) {
        printf("El número del pin es un entero.\n");
        return 1;
    }
    if (gpio == SIN_PIN) {
        if (!pin_opcional(argv[1])) {
            printf("Solo pwdn y reset pueden quedar sin conectar (-1).\n");
            return 1;
        }
    } else {
        std::string motivo;
        if (!gpio_utilizable(gpio, motivo)) {
            printf("No sirve: %s.\n", motivo.c_str());
            return 1;
        }
        if (gpio_de_arranque(gpio)) {
            printf("Ojo: el GPIO %d es un pin de arranque del ESP32-S3.\n", gpio);
        }
    }
    *campo = gpio;
    if (!guardar(c)) {
        return 1;
    }
    printf("Pin %s = %d. Se usa al reiniciar.\n", argv[1], gpio);
    return 0;
}

int cmd_puerta(int argc, char** argv)
{
    if (argc != 3) {
        return uso("puerta <pin> <segundos>   -1 si no hay LED ni relé; por ejemplo: puerta 2 3");
    }
    int gpio = 0;
    int segundos = 0;
    if (!leer_entero(argv[1], gpio) || !leer_entero(argv[2], segundos)) {
        printf("El pin y los segundos son enteros.\n");
        return 1;
    }
    if (gpio != SIN_PIN) {
        std::string motivo;
        if (!gpio_utilizable(gpio, motivo)) {
            printf("No sirve: %s.\n", motivo.c_str());
            return 1;
        }
    }
    if (segundos < 1 || segundos > 60) {
        printf("La puerta queda abierta de 1 a 60 s.\n");
        return 1;
    }
    Config c = config_leer();
    c.puerta_pin = gpio;
    c.puerta_segundos = segundos;
    if (!guardar(c)) {
        return 1;
    }
    printf("Puerta guardada: GPIO %d, %d s.\n", gpio, segundos);
    return 0;
}

int cmd_cara_min(int argc, char** argv)
{
    if (argc != 2) {
        return uso("cara_min <px>   igual que CARA_MIN_PX del servidor (80 por defecto)");
    }
    int px = 0;
    if (!leer_entero(argv[1], px) || px < 1 || px > 240) {
        printf("cara_min va de 1 a 240 px, el alto del cuadro.\n");
        return 1;
    }
    Config c = config_leer();
    c.cara_min = px;
    if (!guardar(c)) {
        return 1;
    }
    printf("cara_min = %d px. Se aplica desde el siguiente cuadro.\n", px);
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
    printf("Comandos (se guardan en la placa y no hace falta recompilar):\n"
           "  estado                         perfil, Wi-Fi, IP, servidor, MQTT y PSRAM\n"
           "  wifi <ssid> <clave>            wifi AccesIA clave123\n"
           "  servidor <url>                 servidor http://10.42.0.1:8000\n"
           "  codigo <codigo>                codigo entrada\n"
           "  token <token>                  el token que da la web al crear la cámara\n"
           "  mqtt <url> <usuario> <clave>   mqtt mqtt://10.42.0.1:1883 camara clave123\n"
           "  perfil [nombre]                perfil generico_octal; sin nombre, lista los de este binario\n"
           "  pin <nombre> <número>          pin xclk 15 (solo perfiles genéricos)\n"
           "  puerta <pin> <segundos>        puerta 2 3; -1 si no hay LED ni relé\n"
           "  cara_min <px>                  cara_min 80\n"
           "  reiniciar                      reinicia la placa\n"
           "  ayuda                          esta lista\n");
    return 0;
}

void registrar(const char* comando, const char* ayuda, esp_console_cmd_func_t funcion)
{
    esp_console_cmd_t cmd = {};
    cmd.command = comando;
    cmd.help = ayuda;
    cmd.func = funcion;
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd));
}

void registrar_comandos()
{
    registrar("estado", "Muestra perfil, Wi-Fi, IP, servidor, MQTT y PSRAM", cmd_estado);
    registrar("wifi", "wifi <ssid> <clave>", cmd_wifi);
    registrar("servidor", "servidor <url>", cmd_servidor);
    registrar("codigo", "codigo <codigo>", cmd_codigo);
    registrar("token", "token <token>", cmd_token);
    registrar("mqtt", "mqtt <url> <usuario> <clave>", cmd_mqtt);
    registrar("perfil", "perfil [nombre]", cmd_perfil);
    registrar("pin", "pin <nombre> <número>", cmd_pin);
    registrar("puerta", "puerta <pin> <segundos>", cmd_puerta);
    registrar("cara_min", "cara_min <px>", cmd_cara_min);
    registrar("reiniciar", "Reinicia la placa", cmd_reiniciar);
    registrar("ayuda", "Lista los comandos", cmd_ayuda);
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

esp_err_t consola_iniciar()
{
    mutex_comandos = xSemaphoreCreateMutex();
    ESP_RETURN_ON_FALSE(mutex_comandos != nullptr, ESP_ERR_NO_MEM, TAG, "Sin memoria para la consola");

    esp_console_config_t config = ESP_CONSOLE_CONFIG_DEFAULT();
    config.max_cmdline_length = LARGO_LINEA;
    config.max_cmdline_args = 8;
    ESP_RETURN_ON_ERROR(esp_console_init(&config), TAG, "No se pudo iniciar esp_console");
    registrar_comandos();
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
