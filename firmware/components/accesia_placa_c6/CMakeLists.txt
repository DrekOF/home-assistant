# Nombre: CMakeLists.txt
# Descripción: Componente accesia_placa_c6: antena, LED de estado y GPIO de la puerta de la XIAO ESP32-C6 (D-21).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Solo existe en el target esp32c6: en otro target se registra vacío, así el S3 puede volver sin tocarlo.

if(NOT IDF_TARGET STREQUAL "esp32c6")
    idf_component_register()
    return()
endif()

idf_component_register(
    SRCS "placa.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_logica
    PRIV_REQUIRES esp_driver_gpio esp_timer accesia_config accesia_consola
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
