# Nombre: CMakeLists.txt
# Descripción: Componente accesia_mqtt: cliente MQTT de la placa según contratos/mqtt.md 1.2.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0

idf_component_register(
    SRCS "mqtt.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_config
    PRIV_REQUIRES mqtt esp_timer accesia_consola accesia_logica
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
