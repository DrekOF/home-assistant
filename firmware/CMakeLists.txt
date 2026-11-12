# Nombre: CMakeLists.txt
# Descripción: Proyecto ESP-IDF 5.4 del firmware de la cámara de AccesIA (frente A).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Hay dos binarios, uno por tipo de PSRAM (D-17). firmware/scripts/compilar-binarios.ps1 compila los dos, cada uno
# con SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.<octal o quad>". Un «idf.py build» sin ese valor
# (por ejemplo, el botón de VS Code) compila el binario octal.

cmake_minimum_required(VERSION 3.16)

if(NOT DEFINED SDKCONFIG_DEFAULTS)
    set(SDKCONFIG_DEFAULTS "sdkconfig.defaults;sdkconfig.defaults.octal")
endif()

set(PROJECT_VER "0.1.0")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(accesia)
