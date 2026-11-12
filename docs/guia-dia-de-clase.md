<!--
Nombre: guia-dia-de-clase.md
Descripción: Guía para montar AccesIA el día de la clase con el hardware que entregue el docente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Guía del día de clase

Meta: pasar de las cajas cerradas a la primera persona reconocida en menos de 45 minutos, sin depender del internet de la universidad. Esta guía se completa el Día 4 con los scripts reales y se prueba el Día 5 con cronómetro.

El hardware ya se conoce (D-21): una Seeed Studio XIAO ESP32-C6 y una Raspberry Pi 5 con Home Assistant OS. La demo usa el escenario 2, en el hotspot de Windows del portátil.

## Antes de salir

- [ ] Kit en el portátil (y copia en una memoria USB si hay):
  - [ ] Las imágenes Docker ya descargadas en el portátil: servidor, PostgreSQL + pgvector, Mosquitto y Ollama. Las arm64 en archivos `.tar` solo hacen falta para el escenario 1.
  - [ ] El modelo de Ollama ya descargado (`qwen2.5:3b` y `qwen2.5:1.5b`).
  - [ ] La copia de seguridad para Home Assistant OS, con la integración MQTT apuntando al portátil.
  - [ ] Los paquetes `.deb` de Docker para arm64 (escenario 1).
  - [ ] El binario del firmware de la XIAO ESP32-C6 y esptool. Los del ESP32-S3 quedan como referencia.
  - [ ] Los scripts `instalar.sh` y `verificar.sh`, y esta guía impresa.
  - [ ] Raspberry Pi Imager, por si hay que grabar el sistema en una memoria USB.
- [ ] El hotspot de Windows del portátil configurado en 2,4 GHz, con el nombre `AccesIA` y su clave.
- [ ] El firewall de Windows deja entrar, en la red del hotspot, el 1883 (MQTT), el 8001 (`mcp`) y el 11434 (`ollama`).
- [ ] El portátil levanta todo con el mismo Compose (plan B).
- [ ] El portátil levanta solo Ollama con `infra/compose.ollama-portatil.yaml`, por si va lento en la Raspberry.
- [ ] Una memoria USB de 32 GB o más, cable USB-C de datos para la XIAO ESP32-C6 y cable de red.
- [ ] Celular con datos para el hotspot (plan B de red).

## Pasos

1. Identificar el hardware. Ya se sabe que es una XIAO ESP32-C6 y una Raspberry Pi 5 con Home Assistant OS (D-21); se confirma el modelo y la RAM de la Raspberry.
2. Montar el sistema según lo que traiga la Raspberry:
   - Escenario 1, Raspberry Pi OS: entrar por SSH con el usuario que dé el docente, copiar el kit desde el portátil y correr `instalar.sh`. El script instala Docker desde los `.deb`, carga las imágenes, copia el modelo y la configuración, crea el Wi-Fi «AccesIA» en 2,4 GHz (`band bg`; la placa no usa 5 GHz) y levanta Docker Compose.
   - Escenario 2, Home Assistant OS, el de la demo (D-21): encender el hotspot del portátil y levantar el servidor, PostgreSQL, Mosquitto y Ollama con `compose.escenario2.yaml`. Después, conectar la Raspberry al hotspot y restaurar nuestra copia de seguridad en Home Assistant; su integración MQTT apunta al broker del portátil (`192.168.137.1:1883`, usuario `homeassistant`).
   - Escenario 3, sin sistema: grabar Raspberry Pi OS en la memoria USB con Raspberry Pi Imager y arrancar desde ella (Pi 5 sin configurar nada; Pi 4 solo si su bootloader ya lo permite). Después, como el escenario 1.
3. Flashear la XIAO ESP32-C6 por el USB-C, con esptool desde el portátil, y configurarla por la consola serial: Wi-Fi del hotspot, código, token, MQTT, sensor y antena.
4. Correr `verificar.sh`: servicios arriba, MQTT, entidades en Home Assistant (también Temperatura y Humedad), Ollama responde y placa en línea.
5. Inscribir a los tres con la misma cámara que va a reconocer, 5 muestras cada uno. Recalibrar `NITIDEZ_MIN` con los valores de `calidad` de esas muestras y ajustar `UMBRAL_SIMILITUD` si hace falta: se cambian en `infra/.env` y se reinicia el servidor (D-14).
6. Ensayo corto de la demo y presentación.

## Planes B

| Si falla | Plan B |
| --- | --- |
| La cámara de la placa no está lista (D-21) | Simulador con la webcam del portátil; la placa sigue abriendo la puerta |
| La XIAO ESP32-C6 no conecta | Simulador con la webcam del portátil, que también simula la puerta |
| La cámara deja de reconocer durante la demo | Registrar las llegadas a mano en la pantalla Asistencia (RF-06 · C5) |
| Ollama va lento en la Raspberry | Ollama en el portátil con `infra/compose.ollama-portatil.yaml`, en la red propia |
| La Raspberry no arranca, o viene sin sistema y no arranca desde USB | Pedir una microSD al docente; si no hay, todo en el portátil con el mismo Compose |
| El hotspot del portátil no funciona | Red del salón o hotspot del celular, reconfigurando la placa por consola |

## Qué preguntarle al docente antes (P-03)

- Qué módulo de cámara llega y cómo se conecta: una cámara SPI para el C6 o una placa con cámara aparte.
- Si en el salón hay red con portal o que aísle los equipos entre sí.
