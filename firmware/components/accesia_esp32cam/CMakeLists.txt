# Nombre: CMakeLists.txt
# Descripción: Componente accesia_esp32cam: la ESP32-CAM AI-Thinker (D-24): ciclo de visión y envío, presencia, LED rojo y comandos de consola.
# Fecha de creación: 2026-11-19
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.0

if(NOT IDF_TARGET STREQUAL "esp32")
    idf_component_register()
    return()
endif()

idf_component_register(
    SRCS "esp32cam.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_config accesia_logica
    PRIV_REQUIRES accesia_camara accesia_consola accesia_deteccion accesia_envio accesia_recorte accesia_vision
                  esp_driver_gpio esp_psram esp_timer
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
