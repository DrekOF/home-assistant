<!--
Nombre: guia-dia-de-clase.md
Descripción: Guía para montar AccesIA el día de la clase con el hardware que entregue el docente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.1
-->

# Guía del día de clase

Meta: pasar de las cajas cerradas a la primera persona reconocida en menos de 45 minutos, sin depender del internet de la universidad. Esta guía se completa el Día 4 con los scripts reales y se prueba el Día 5 con cronómetro.

## Antes de salir

- [ ] Kit en el portátil (y copia en una memoria USB si hay):
  - [ ] Imágenes Docker arm64 en archivos `.tar`: servidor, PostgreSQL + pgvector, Mosquitto, Home Assistant y Ollama.
  - [ ] El modelo de Ollama ya descargado (`qwen2.5:3b` y `qwen2.5:1.5b`).
  - [ ] La configuración de Home Assistant y una copia de seguridad para Home Assistant OS.
  - [ ] Los paquetes `.deb` de Docker para arm64.
  - [ ] Los dos binarios del firmware (`octal` y `quad`), el de diagnóstico, el de respaldo y esptool.
  - [ ] Los scripts `instalar.sh` y `verificar.sh`, y esta guía impresa.
  - [ ] Raspberry Pi Imager, por si hay que grabar el sistema en una memoria USB.
- [ ] El portátil levanta todo con el mismo Compose (plan B).
- [ ] El portátil levanta solo Ollama con `infra/compose.ollama-portatil.yaml`, por si va lento en la Raspberry.
- [ ] Una memoria USB de 32 GB o más, cable USB de datos para el ESP32-S3 y cable de red.
- [ ] Celular con datos para el hotspot (plan B de red).

## Pasos

1. Identificar el hardware: la placa ESP32-S3 por su serigrafía (o con el firmware de diagnóstico) y el modelo, la RAM y el sistema de la Raspberry.
2. Montar el sistema según lo que traiga la Raspberry:
   - Escenario 1, Raspberry Pi OS: entrar por SSH con el usuario que dé el docente, copiar el kit desde el portátil y correr `instalar.sh`. El script instala Docker desde los `.deb`, carga las imágenes, copia el modelo y la configuración, crea el Wi-Fi «AccesIA» en 2,4 GHz (`band bg`; el ESP32-S3 no usa 5 GHz) y levanta Docker Compose.
   - Escenario 2, Home Assistant OS: restaurar nuestra copia de seguridad en Home Assistant. El servidor, PostgreSQL, Mosquitto y Ollama corren en el portátil con `compose.escenario2.yaml`, en la red del salón o en el hotspot.
   - Escenario 3, sin sistema: grabar Raspberry Pi OS en la memoria USB con Raspberry Pi Imager y arrancar desde ella (Pi 5 sin configurar nada; Pi 4 solo si su bootloader ya lo permite). Después, como el escenario 1.
3. Flashear el ESP32-S3 con el binario de su PSRAM (`octal` o `quad`, según el diagnóstico), con esptool desde el portátil, y configurarlo por la consola serial (perfil, Wi-Fi, servidor, código, token y MQTT).
4. Correr `verificar.sh`: servicios arriba, MQTT, entidades en Home Assistant, Ollama responde y cámara en línea.
5. Inscribir a los tres con la misma cámara que va a reconocer, 5 muestras cada uno. Recalibrar `NITIDEZ_MIN` con los valores de `calidad` de esas muestras y ajustar `UMBRAL_SIMILITUD` si hace falta: se cambian en `infra/.env` y se reinicia el servidor (D-14).
6. Ensayo corto de la demo y presentación.

## Planes B

| Si falla | Plan B |
| --- | --- |
| El firmware TinyML no arranca en la placa | Firmware de respaldo y modo extraer del servidor |
| El ESP32-S3 no conecta | Simulador con la webcam del portátil |
| La cámara deja de reconocer durante la demo | Registrar las llegadas a mano en la pantalla Asistencia (RF-06 · C5) |
| Ollama va lento en la Raspberry | Ollama en el portátil con `infra/compose.ollama-portatil.yaml`, en la red propia |
| La Raspberry no arranca, o viene sin sistema y no arranca desde USB | Pedir una microSD al docente; si no hay, todo en el portátil con el mismo Compose |
| El Wi-Fi propio no funciona | Red del salón o hotspot del celular, reconfigurando el ESP32-S3 por consola |

## Qué preguntarle al docente antes (P-02)

- Qué placa ESP32-S3 entregan y si trae cámara.
- Qué Raspberry (modelo y RAM), qué sistema trae, si trae microSD y con qué usuario se entra.
- Si en el salón hay red con portal o que aísle los equipos entre sí.
