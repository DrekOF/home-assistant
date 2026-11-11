<!--
Nombre: README.md
Descripción: Firmware de la cámara ESP32-S3 de AccesIA (frente A).
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Firmware de la cámara · frente A

Firmware del ESP32-S3 en ESP-IDF (C++): detecta la cara con TinyML (ESP-DL), envía el recorte al servidor por HTTP y abre la puerta cuando Home Assistant lo pide por MQTT.

- Specs: `specs/arquitectura.md` (Firmware de la cámara), `specs/requisitos.md` (RF-01) y los contratos `api-dispositivo.md` y `mqtt.md`.
- Lo crea la tarea `tareas/dia-1/A-julian-esp-idf-y-deteccion.md`. El envío y la puerta son del Día 3; los binarios por perfil, el diagnóstico y el respaldo, del Día 4.

## Comandos

Se completan con la tarea A del Día 1.

Si una herramienta pide la carpeta vacía para crear el proyecto, créalo en una carpeta temporal y mueve los archivos aquí. Este README se conserva y se completa.
