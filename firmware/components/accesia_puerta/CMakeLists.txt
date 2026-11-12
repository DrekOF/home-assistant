# Nombre: CMakeLists.txt
# Descripción: Componente accesia_puerta: la salida de la puerta (LED o relé), su nivel activo y su cierre por tiempo.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0

idf_component_register(
    SRCS "puerta.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_config
    PRIV_REQUIRES esp_driver_gpio esp_timer accesia_logica
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
