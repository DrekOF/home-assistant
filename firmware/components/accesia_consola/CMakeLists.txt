# Nombre: CMakeLists.txt
# Descripción: Componente accesia_consola: comandos de arquitectura.md por UART0 y por el USB nativo, guardados en NVS.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0

idf_component_register(
    SRCS "consola.cpp"
    INCLUDE_DIRS "include"
    PRIV_REQUIRES console esp_driver_uart esp_driver_usb_serial_jtag esp_psram accesia_config accesia_perfiles
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
