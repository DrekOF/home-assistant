# Nombre: CMakeLists.txt
# Descripción: Componente accesia_config: configuración común de la placa en NVS y claves propias de cada componente.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.1

idf_component_register(
    SRCS "config.cpp"
    INCLUDE_DIRS "include"
    PRIV_REQUIRES nvs_flash esp_app_format
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
