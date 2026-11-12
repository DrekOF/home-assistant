# Nombre: CMakeLists.txt
# Descripción: Componente main del firmware: arranque, consola y bucle de detección.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0

idf_component_register(
    SRCS "main.cpp"
    PRIV_REQUIRES accesia_camara accesia_config accesia_consola accesia_deteccion accesia_perfiles accesia_recorte
                  esp_timer
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
