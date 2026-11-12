# Nombre: CMakeLists.txt
# Descripción: Componente accesia_logica: mensajes MQTT, puerta, ambiente, LED y pines de la placa (lógica pura).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# C++17 sin cabeceras de ESP-IDF: firmware/pruebas/ compila los mismos archivos en Linux.

idf_component_register(
    SRCS "mensajes.cpp" "puerta_logica.cpp" "ambiente_logica.cpp" "led.cpp" "placa_c6.cpp"
    INCLUDE_DIRS "include"
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Werror)
