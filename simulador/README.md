<!--
Nombre: README.md
Descripción: Simulador de la cámara de AccesIA con la webcam (frente A).
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Simulador · frente A

Hace lo mismo que la cámara con la webcam del portátil o con una carpeta de fotos: detecta con YuNet, recorta con 25 % de margen y envía al servidor. También simula la puerta por MQTT. Sirve para desarrollar sin hardware y es el plan C de la demo (D-10).

- Specs: `specs/arquitectura.md` (Simulador) y los contratos `api-dispositivo.md` y `mqtt.md`.
- Se construye el Día 2 (`specs/plan.md`). Las fotos de prueba van en `datos/prueba/`, que Git ignora.

## Comandos

Se completan con la tarea del simulador.

Si una herramienta pide la carpeta vacía para crear el proyecto, créalo en una carpeta temporal y mueve los archivos aquí. Este README se conserva y se completa.
