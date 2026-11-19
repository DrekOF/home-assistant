# Nombre: CMakeLists.txt
# Descripción: Componente accesia_recorte: cara de mayor área, fórmula del recorte, cara_min, espera entre recortes y lógica del envío.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.1
#
# Lógica pura en C++17, sin cabeceras de ESP-IDF: firmware/pruebas/ compila los mismos archivos en Linux.

idf_component_register(
    SRCS "recorte.cpp" "espera.cpp" "envio_logica.cpp"
    INCLUDE_DIRS "include"
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Werror)
