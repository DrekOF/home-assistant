# Nombre: CMakeLists.txt
# Descripción: Componente accesia_deteccion: caras con ESP-DL 1.1 (HumanFaceDetectMSR01 + MNP01) en la ESP32-CAM (D-24, P-05).
# Fecha de creación: 2026-11-19
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Solo en el target esp32: espressif/esp-dl 1.1.0 se declara para él en main/idf_component.yml. Trae sus
# bibliotecas ya compiladas para el ESP32 clásico; human_face_detect, de ESP-DL 3, solo tiene modelos del S3 y del P4.

if(NOT IDF_TARGET STREQUAL "esp32")
    idf_component_register()
    return()
endif()

idf_component_register(
    SRCS "deteccion.cpp"
    INCLUDE_DIRS "include"
    REQUIRES accesia_vision
    PRIV_REQUIRES espressif__esp-dl
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
