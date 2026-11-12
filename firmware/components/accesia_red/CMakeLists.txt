# Nombre: CMakeLists.txt
# Descripción: Componente accesia_red: Wi-Fi de la placa en modo estación, con reconexión sola.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0

idf_component_register(
    SRCS "red.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_config
    PRIV_REQUIRES esp_wifi esp_netif esp_event esp_timer accesia_consola
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
