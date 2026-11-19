# Nombre: CMakeLists.txt
# Descripción: Componente accesia_envio: envía el JPEG del recorte al servidor por HTTP (api-dispositivo.md 1.2) y lee su respuesta.
# Fecha de creación: 2026-11-19
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Solo en el target esp32: en la XIAO ESP32-C6 no hay cámara (D-21).

if(NOT IDF_TARGET STREQUAL "esp32")
    idf_component_register()
    return()
endif()

idf_component_register(
    SRCS "envio.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_recorte
    PRIV_REQUIRES esp_http_client json
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
