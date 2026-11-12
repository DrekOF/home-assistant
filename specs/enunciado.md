<!--
Nombre: enunciado.md
Descripción: Enunciado del docente y dónde se cumple cada parte en AccesIA.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Enunciado

## Texto del docente

> Se debe crear un software para la identificacion personal usando el reconocimiento facial con inscripcion, registrar el rostro de alguien y comparar el nuevo rostro detectado contra las identidades faciales registradas (control de acceso + control de asistencia (access control + assistant control)), para ello se debe emplear dentro del software que se haga home assistant integration con tinymlmodel, agente de ia, base de datos en postgreSQL y ollama local, con el fin de que el software que se haga sea compatible con un raspberry pi (home assistant), esp32-s3 (camara)(tinymlmodel) como hardware externo.

Interpretación: «assistant control» se entiende como control de **asistencia** (quién llegó y a qué hora).

## Dónde se cumple cada parte

| Lo que pide | Cómo lo cumple AccesIA | Dónde |
| --- | --- | --- |
| Identificación personal con reconocimiento facial | El servidor saca la huella de la cara (SFace, 128 números) y la busca en PostgreSQL con pgvector | RF-04, R1, R2 |
| Inscripción: registrar el rostro de alguien | Inscripción con consentimiento y 5 muestras tomadas desde la cámara | RF-02, RF-03, R7, R9 |
| Comparar el rostro nuevo contra los registrados | Similitud de coseno contra todas las muestras; cuenta la más parecida | RF-04, R1, R2 |
| Control de acceso | Regla de acceso en el servidor y puerta abierta por Home Assistant | RF-05, RF-07, R3, R4 |
| Control de asistencia | La primera entrada permitida del día es la llegada, a tiempo o tarde; sin consentimiento, o si la cámara falla, se registra a mano | RF-06, R5 |
| Integración con Home Assistant | MQTT con descubrimiento automático, panel y automatizaciones | RF-07, `contratos/mqtt.md` |
| Modelo TinyML | Detección de caras de ESP-DL (int8) dentro del ESP32-S3. Ver «Hardware entregado» | RF-01, D-02, D-21 |
| Agente de IA | Ollama con herramientas de solo lectura (MCP), usado desde Assist | RF-08, `contratos/mcp-agente.md` |
| Base de datos PostgreSQL | PostgreSQL 18 con pgvector | `modelo-datos.md`, `contratos/base-de-datos.sql` |
| Ollama local | Ollama en la Raspberry o, si va lento, en un portátil de la misma red. Ver «Hardware entregado» | D-06, D-21 |
| Compatible con Raspberry Pi (Home Assistant) | Todo en Docker Compose con imágenes arm64. Ver «Hardware entregado» | RNF-04, D-09, D-21 |
| ESP32-S3 con cámara como hardware externo | Firmware ESP-IDF con perfiles de placa. Ver «Hardware entregado» | RF-01, RF-14, `arquitectura.md` |

## Hardware entregado el 12/11/2026

En clase entregaron una Seeed Studio XIAO ESP32-C6 (4 MB de flash, sin PSRAM ni interfaz de cámara), no un ESP32-S3, y una Raspberry Pi 5 con Home Assistant OS. El módulo de cámara llega la próxima clase. Así cambia lo de arriba (D-21):

- Modelo TinyML: la detección en la placa espera al módulo de cámara. Mientras tanto, la cámara es el simulador, y el firmware del ESP32-S3 con ESP-DL queda como referencia (PR #7).
- Hardware externo: la XIAO ESP32-C6 es la placa del punto de acceso. Abre la puerta con un LED y publica por MQTT, hacia Home Assistant, su estado y un sensor de temperatura y humedad (RF-14).
- Raspberry Pi: trae Home Assistant OS. El servidor, PostgreSQL, Mosquitto y Ollama corren en un portátil junto a ella (escenario 2), en el hotspot de Windows del portátil.
