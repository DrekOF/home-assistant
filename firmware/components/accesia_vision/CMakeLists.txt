# Nombre: CMakeLists.txt
# Descripción: Componente accesia_vision: interfaces de la fuente de cuadros y del detector, que implementa la ESP32-CAM (D-24).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.1

idf_component_register(
    INCLUDE_DIRS "include"
    REQUIRES accesia_recorte
)
