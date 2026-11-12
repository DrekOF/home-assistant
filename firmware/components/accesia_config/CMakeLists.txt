# Nombre: CMakeLists.txt
# Descripción: Componente accesia_config: configuración de la cámara en NVS, con los valores por defecto de arquitectura.md.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0

idf_component_register(
    SRCS "config.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_perfiles
    PRIV_REQUIRES nvs_flash esp_app_format
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
