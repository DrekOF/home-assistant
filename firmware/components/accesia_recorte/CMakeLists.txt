# Nombre: CMakeLists.txt
# Descripción: Componente accesia_recorte: cara de mayor área, fórmula del recorte, cara_min y espera entre recortes.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Lógica pura en C++17, sin cabeceras de ESP-IDF: firmware/pruebas/ compila los mismos archivos en Linux.

idf_component_register(
    SRCS "recorte.cpp" "espera.cpp"
    INCLUDE_DIRS "include"
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Werror)
