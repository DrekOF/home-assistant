# Nombre: CMakeLists.txt
# Descripción: Componente accesia_ambiente: sensor DHT22 o DHT11 de la XIAO ESP32-C6, leído cada 30 s (D-21).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Solo existe en el target esp32c6: en otro target se registra vacío, así el S3 puede volver sin tocarlo.
# esp-idf-lib/dht se declara, con su versión fija, en main/idf_component.yml.

if(NOT IDF_TARGET STREQUAL "esp32c6")
    idf_component_register()
    return()
endif()

idf_component_register(
    SRCS "ambiente.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_logica
    PRIV_REQUIRES esp-idf-lib__dht esp_timer accesia_config accesia_consola
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
