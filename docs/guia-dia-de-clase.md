<!--
Nombre: guia-dia-de-clase.md
Descripción: Guía para montar AccesIA el día de la clase con el hardware que entregue el docente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.5
-->

# Guía del día de clase

Meta: pasar de las cajas cerradas a la primera persona reconocida en menos de 45 minutos, sin depender del internet de la universidad. Esta guía se completa el Día 4 con los scripts reales y se prueba el Día 5 con cronómetro.

El hardware ya se conoce (D-21): una Seeed Studio XIAO ESP32-C6 y una Raspberry Pi 5 con Home Assistant OS. En la demo todo corre en la Pi, como complementos de Home Assistant OS, en el hotspot de Windows del portátil (D-22). El escenario 2, con el resto en el portátil, queda como plan B.

## Antes de salir

- [ ] Kit en el portátil (y copia en una memoria USB si hay):
  - [ ] Las carpetas de los complementos `accesia_base` y `accesia_servidor`, armadas con `scripts/empaquetar-complementos.ps1`, con los modelos de cara (D-22).
  - [ ] Los archivos del modelo de Ollama, para copiarlos a `/share/ollama` sin internet: los que se vayan a usar según la RAM de la Pi.
  - [ ] La copia de seguridad cifrada de Home Assistant OS, sin inscripciones, con su clave de cifrado guardada aparte.
  - [ ] `kit\firmware`, armado con `firmware\scripts\armar-kit.ps1`: el binario de la XIAO ESP32-C6 y, por si llega un ESP32-S3, los binarios octal y quad del PR #7, con `flashear.ps1`. esptool viene con ESP-IDF.
  - [ ] Para el plan B, las imágenes Docker ya descargadas en el portátil: servidor, PostgreSQL + pgvector y Mosquitto.
  - [ ] Para el plan C (escenarios 1 y 3): las imágenes arm64 en archivos `.tar`, los paquetes `.deb` de Docker para arm64, `instalar.sh`, `verificar.sh` y Raspberry Pi Imager.
  - [ ] El script `verificar` del portátil y esta guía impresa.
- [ ] Si la Pi está disponible antes de la clase, los complementos ya instalados en ella. Si no, el celular con datos para instalarlos en clase: construirlos necesita internet una vez.
- [ ] El hotspot de Windows del portátil configurado en 2,4 GHz, con el nombre `AccesIA` y su clave.
- [ ] El portátil levanta todo con el mismo Compose y con `compose.escenario2.yaml` (plan B). El firewall de Windows se abre solo si se usa; los puertos están en `specs/arquitectura.md` («Red y despliegue»).
- [ ] Ollama en el portátil, con `infra/compose.ollama-portatil.yaml`, solo si el docente lo aprueba.
- [ ] Una memoria USB de 32 GB o más, cable USB-C de datos para la XIAO ESP32-C6 y cable de red.
- [ ] Celular con datos para el hotspot (plan B de red).

## Pasos

1. Identificar el hardware. Ya se sabe que es una XIAO ESP32-C6 y una Raspberry Pi 5 con Home Assistant OS (D-21); se confirma el modelo y la RAM de la Raspberry, que decide el modelo de Ollama (D-22).
2. Montar el sistema:
   - La demo (D-22), con Home Assistant OS:
     1. Encender el hotspot del portátil, conectar la Raspberry y ponerle su IP fija en la configuración de red de Home Assistant OS.
     2. Si no trae los complementos, instalarlos como dice `specs/arquitectura.md` («Complementos de Home Assistant OS»): los dos nuestros, el Mosquitto oficial y el de Ollama. Construirlos necesita internet: el del celular.
     3. Copiar el modelo de Ollama a `/share/ollama` por Samba, sin internet.
     4. Restaurar nuestra copia de seguridad de Home Assistant, o poner a mano las opciones de cada complemento: claves, reglas, los `logins` de Mosquitto y su ACL.
     5. Arrancar la base y después el servidor.
   - Plan B, escenario 2: la base, el servidor y Mosquitto en el portátil con `compose.escenario2.yaml`, abriendo el firewall para el hotspot. La integración MQTT de Home Assistant apunta al broker del portátil (`192.168.137.1:1883`, usuario `homeassistant`), y Ollama sigue en la Raspberry.
   - Plan C, escenario 1, Raspberry Pi OS: entrar por SSH con el usuario que dé el docente, copiar el kit desde el portátil y correr `instalar.sh`. El script instala Docker desde los `.deb`, carga las imágenes, copia el modelo y la configuración, crea el Wi-Fi «AccesIA» en 2,4 GHz (`band bg`; la placa no usa 5 GHz) y levanta Docker Compose.
   - Plan C, escenario 3, sin sistema: grabar Raspberry Pi OS en la memoria USB con Raspberry Pi Imager y arrancar desde ella (Pi 5 sin configurar nada; Pi 4 solo si su bootloader ya lo permite). Después, como el escenario 1.
3. Flashear la XIAO ESP32-C6 por el USB-C con `kit\firmware\flashear.ps1 -Placa c6 -Puerto COMx`, que dice cómo ponerla en modo de descarga. Sus valores de fábrica ya apuntan a la Pi (`192.168.137.250`, D-22). Por la consola serial faltan la clave del Wi-Fi del hotspot, el código, el token, la clave de MQTT (`mqtt mqtt://192.168.137.250:1883 camara <clave>`), el sensor y la antena. Si la Pi quedó en otra IP, también `servidor` y `mqtt` con esa IP.
4. Correr `verificar` desde el portátil: complementos arriba, MQTT, entidades en Home Assistant (también Temperatura y Humedad), Ollama responde y placa en línea.
5. Inscribir a los tres con la misma cámara que va a reconocer, 5 muestras cada uno. Recalibrar `NITIDEZ_MIN` con los valores de `calidad` de esas muestras y ajustar `UMBRAL_SIMILITUD` si hace falta: se cambian en las opciones de `accesia_servidor` y se reinicia el complemento (D-14 y D-22); en el plan B, en `infra/.env`.
6. Ensayo corto de la demo y presentación.

## Planes B

| Si falla | Plan B |
| --- | --- |
| La cámara de la placa no está lista (D-21) | Simulador con la webcam del portátil, con `--servidor http://192.168.137.250:8000`; la placa sigue abriendo la puerta |
| Llega un ESP32-CAM, o un celular hace de cámara | Cámara de respaldo: el servidor le pide una foto por segundo por HTTP, sin tocar su firmware (RF-10 · C4). Se registra con su URL de captura, como dice `servidor/README.md` («Registrar una cámara de respaldo, paso a paso») |
| La XIAO ESP32-C6 no conecta | Simulador con la webcam del portátil, que también simula la puerta |
| La cámara deja de reconocer durante la demo | Registrar las llegadas a mano en la pantalla Asistencia (RF-06 · C5) |
| Ollama va lento en la Raspberry | Primero, en la Raspberry: las variantes Q4_0, descripciones más cortas, `qwen2.5:0.5b` si responde bien y el comienzo del prompt estable (RNF-03 · C3). Ollama en el portátil, con `infra/compose.ollama-portatil.yaml`, solo con el visto bueno del docente |
| La Raspberry no alcanza para la base y el servidor | Escenario 2: la base, el servidor y Mosquitto en el portátil con `compose.escenario2.yaml`; Home Assistant y Ollama siguen en la Raspberry |
| No hay internet para instalar los complementos | El celular con datos; si tampoco hay, el escenario 2 |
| La Raspberry no arranca, o viene sin sistema y no arranca desde USB | Pedir una microSD al docente; si no hay, todo en el portátil con el mismo Compose |
| El hotspot del portátil no funciona | Red del salón o hotspot del celular, reconfigurando la placa por consola |

## Qué preguntarle al docente antes (P-03 y P-04)

- Qué módulo de cámara llega y cómo se conecta: una cámara SPI para el C6 o una placa con cámara aparte.
- Si en el salón hay red con portal o que aísle los equipos entre sí.
- Si la Raspberry está disponible antes de la clase, para instalar los complementos con tiempo, y cuánta RAM tiene (D-22).
