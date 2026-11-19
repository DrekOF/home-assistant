# Nombre: CMakeLists.txt
# Descripción: Proyecto ESP-IDF 5.4 del firmware de AccesIA (frente A). En la demo es la ESP32-CAM AI-Thinker (D-24).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.2
#
# El target lo elige quien compila: firmware/scripts/compilar.ps1 pasa -D IDF_TARGET, igual que «idf.py
# set-target». Si nadie lo eligió, es esp32, la ESP32-CAM de D-24. ESP-IDF suma solo sdkconfig.defaults.<target>
# al común. La XIAO ESP32-C6 (esp32c6, D-21) sigue compilando, aunque ya no se usa. El ESP32-S3 de referencia
# (PR #7) puede volver como otro target, con sus componentes protegidos por target.

cmake_minimum_required(VERSION 3.16)

if(NOT DEFINED IDF_TARGET AND NOT DEFINED ENV{IDF_TARGET} AND NOT DEFINED SDKCONFIG
   AND NOT EXISTS "${CMAKE_CURRENT_LIST_DIR}/sdkconfig")
    set(IDF_TARGET esp32)
endif()

set(PROJECT_VER "0.3.0")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# Un dependencies.lock por target, para que compilar uno no reescriba el del otro.
idf_build_set_property(DEPENDENCIES_LOCK "${CMAKE_CURRENT_LIST_DIR}/dependencies.lock.${IDF_TARGET}")

project(accesia)

# ESP-DL 1.1 (solo en la ESP32-CAM) le pasa al enlazador «-L <carpeta>» como un solo argumento. Si la ruta del
# repositorio tiene un espacio, como «Inteligencia artificial», el enlazador la corta y no encuentra sus
# bibliotecas. Se cambia por la misma carpeta como directorio de enlace, que CMake sí pone entre comillas.
if(IDF_TARGET STREQUAL "esp32")
    idf_component_get_property(espdl_lib espressif__esp-dl COMPONENT_LIB)
    idf_component_get_property(espdl_dir espressif__esp-dl COMPONENT_DIR)
    get_target_property(espdl_enlaces ${espdl_lib} INTERFACE_LINK_LIBRARIES)
    list(FILTER espdl_enlaces EXCLUDE REGEX "^-L")
    set_property(TARGET ${espdl_lib} PROPERTY INTERFACE_LINK_LIBRARIES "${espdl_enlaces}")
    set_property(TARGET ${espdl_lib} APPEND PROPERTY INTERFACE_LINK_DIRECTORIES "${espdl_dir}/lib/esp32")
endif()
