# Nombre: CMakeLists.txt
# Descripción: Componente accesia_camara: cámara con esp32-camera según el perfil y JPEG del recorte en memoria.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# espressif/esp32-camera se declara, con su versión fija, en main/idf_component.yml.

idf_component_register(
    SRCS "camara.cpp"
    INCLUDE_DIRS "include"
    REQUIRES espressif__esp32-camera accesia_perfiles accesia_recorte
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
