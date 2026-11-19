/**
 * Nombre: envio.cpp
 * Descripción: POST del recorte con esp_http_client y lectura de la respuesta con cJSON (api-dispositivo.md 1.2).
 * Fecha de creación: 2026-11-19
 * Actualización: 2026-11-19
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

#include "accesia/envio.hpp"

#include <strings.h>

#include "cJSON.h"
#include "esp_http_client.h"
#include "esp_log.h"

namespace accesia {
namespace {

constexpr const char* TAG = "envio";
constexpr std::size_t CUERPO_MAXIMO = 4096;  // la respuesta 200 del contrato ocupa menos de 1 KB

struct Lectura {
    std::string cuerpo;
    std::optional<int> reintentar_s;
};

esp_err_t al_evento(esp_http_client_event_t* evento)
{
    auto* lectura = static_cast<Lectura*>(evento->user_data);
    switch (evento->event_id) {
    case HTTP_EVENT_ON_HEADER:
        if (evento->header_key != nullptr && evento->header_value != nullptr &&
            strcasecmp(evento->header_key, "Retry-After") == 0) {
            lectura->reintentar_s = leer_reintentar(evento->header_value);
        }
        break;
    case HTTP_EVENT_ON_DATA:
        if (evento->data_len > 0 && lectura->cuerpo.size() + static_cast<std::size_t>(evento->data_len) <= CUERPO_MAXIMO) {
            lectura->cuerpo.append(static_cast<const char*>(evento->data), static_cast<std::size_t>(evento->data_len));
        }
        break;
    default:
        break;
    }
    return ESP_OK;
}

std::string campo_texto(const cJSON* raiz, const char* nombre)
{
    const cJSON* campo = cJSON_GetObjectItemCaseSensitive(raiz, nombre);
    return cJSON_IsString(campo) && campo->valuestring != nullptr ? campo->valuestring : "";
}

}  // namespace

RespuestaEnvio envio_enviar(const std::string& url, const std::string& token, const std::string& firmware,
                            const std::uint8_t* jpeg, std::size_t bytes, float puntaje)
{
    RespuestaEnvio respuesta;
    Lectura lectura;

    esp_http_client_config_t config = {};
    config.url = url.c_str();
    config.method = HTTP_METHOD_POST;
    config.timeout_ms = TIEMPO_ESPERA_HTTP_MS;
    config.disable_auto_redirect = true;
    config.event_handler = al_evento;
    config.user_data = &lectura;

    esp_http_client_handle_t cliente = esp_http_client_init(&config);
    if (cliente == nullptr) {
        respuesta.error_red = "no se pudo crear el cliente HTTP";
        return respuesta;
    }
    // esp_http_client copia el valor de cada cabecera; el cuerpo lo lee del JPEG mientras envía.
    const std::string autorizacion = "Bearer " + token;
    const std::string puntaje_texto = texto_puntaje(puntaje);
    esp_http_client_set_header(cliente, "Authorization", autorizacion.c_str());
    esp_http_client_set_header(cliente, "Content-Type", "image/jpeg");
    esp_http_client_set_header(cliente, "X-AccesIA-Firmware", firmware.c_str());
    esp_http_client_set_header(cliente, "X-AccesIA-Puntaje", puntaje_texto.c_str());
    esp_http_client_set_post_field(cliente, reinterpret_cast<const char*>(jpeg), static_cast<int>(bytes));

    const esp_err_t err = esp_http_client_perform(cliente);
    if (err == ESP_OK) {
        respuesta.http = esp_http_client_get_status_code(cliente);
    } else {
        respuesta.error_red = esp_err_to_name(err);
    }
    esp_http_client_cleanup(cliente);
    respuesta.reintentar_s = lectura.reintentar_s;

    if (!lectura.cuerpo.empty()) {
        cJSON* raiz = cJSON_ParseWithLength(lectura.cuerpo.c_str(), lectura.cuerpo.size());
        if (raiz != nullptr) {
            if (respuesta.http == 200) {
                respuesta.resultado = campo_texto(raiz, "resultado");
                respuesta.mensaje = campo_texto(raiz, "mensaje");
            } else {
                respuesta.codigo_error = campo_texto(raiz, "codigo");
                respuesta.mensaje = campo_texto(raiz, "detalle");
            }
            cJSON_Delete(raiz);
        } else {
            ESP_LOGW(TAG, "La respuesta del servidor (HTTP %d) no es JSON.", respuesta.http);
        }
    }
    return respuesta;
}

}  // namespace accesia
