# Nombre: CMakeLists.txt
# Descripción: Componente accesia_consola: comandos de arquitectura.md por UART0 y por el USB nativo, guardados en NVS.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.1

idf_component_register(
    SRCS "consola.cpp"
    INCLUDE_DIRS "include"
    REQUIRES console
    PRIV_REQUIRES esp_driver_uart esp_driver_usb_serial_jtag accesia_config
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
