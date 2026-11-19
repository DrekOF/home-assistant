# Nombre: CMakeLists.txt
# Descripción: Componente accesia_camara: la OV2640 de la ESP32-CAM con esp32-camera, en QVGA y RGB565, y el JPEG del recorte (D-24).
# Fecha de creación: 2026-11-19
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Solo en el target esp32: espressif/esp32-camera se declara para él en main/idf_component.yml.

if(NOT IDF_TARGET STREQUAL "esp32")
    idf_component_register()
    return()
endif()

idf_component_register(
    SRCS "camara.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_vision accesia_recorte
    PRIV_REQUIRES espressif__esp32-camera esp_driver_gpio accesia_logica
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
