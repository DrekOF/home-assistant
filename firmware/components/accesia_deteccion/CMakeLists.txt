# Nombre: CMakeLists.txt
# Descripción: Componente accesia_deteccion: HumanFaceDetect de ESP-DL con el modelo MSR + MNP en int8 (RF-01 · C1).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# espressif/human_face_detect y espressif/esp-dl se declaran, con sus versiones fijas, en main/idf_component.yml.

idf_component_register(
    SRCS "deteccion.cpp"
    INCLUDE_DIRS "include"
    REQUIRES espressif__esp32-camera accesia_recorte
    PRIV_REQUIRES espressif__human_face_detect espressif__esp-dl
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra)
