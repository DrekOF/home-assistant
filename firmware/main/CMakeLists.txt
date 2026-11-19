# Nombre: CMakeLists.txt
# Descripción: Componente main del firmware: arranque de la placa con sus componentes comunes y los de su target.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.1

set(requeridos accesia_config accesia_consola accesia_logica accesia_mqtt accesia_puerta accesia_red esp_timer)
if(IDF_TARGET STREQUAL "esp32")
    list(APPEND requeridos accesia_esp32cam)
elseif(IDF_TARGET STREQUAL "esp32c6")
    list(APPEND requeridos accesia_ambiente accesia_placa_c6)
endif()

idf_component_register(
    SRCS "main.cpp"
    PRIV_REQUIRES ${requeridos}
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
