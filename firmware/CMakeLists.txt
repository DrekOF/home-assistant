# Nombre: CMakeLists.txt
# Descripción: Proyecto ESP-IDF 5.4 del firmware de AccesIA (frente A). En la demo es la XIAO ESP32-C6 (D-21).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.1
#
# El target lo elige quien compila: firmware/scripts/compilar.ps1 pasa -D IDF_TARGET, igual que «idf.py
# set-target». Si nadie lo eligió, es esp32c6. ESP-IDF suma solo sdkconfig.defaults.<target> al común.
# El ESP32-S3 de referencia (PR #7) puede volver como otro target, con sus componentes protegidos por target.

cmake_minimum_required(VERSION 3.16)

if(NOT DEFINED IDF_TARGET AND NOT DEFINED ENV{IDF_TARGET} AND NOT DEFINED SDKCONFIG
   AND NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/sdkconfig")
    set(IDF_TARGET esp32c6)
endif()

set(PROJECT_VER "0.2.0")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# Un dependencies.lock por target, para que compilar uno no reescriba el del otro.
idf_build_set_property(DEPENDENCIES_LOCK "${CMAKE_CURRENT_LIST_DIR}/dependencies.lock.${IDF_TARGET}")

project(accesia)
