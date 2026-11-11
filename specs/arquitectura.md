<!--
Nombre: arquitectura.md
Descripción: Piezas de AccesIA, flujos, servicios, puertos, configuración, firmware y despliegue.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Arquitectura

**La cámara ve, el servidor reconoce, Home Assistant actúa y el agente responde.** Todo, menos la cámara, corre con Docker Compose en la Raspberry Pi (o en un portátil, según el escenario).

Los diagramas están en `docs/diagramas/`: `arquitectura-explicada.html` (quién hace qué) y `paso-a-paso.html` (el recorrido).

## Piezas

| Pieza | Qué hace | Tecnología | Frente | Carpeta |
| --- | --- | --- | --- | --- |
| Cámara | Detecta la cara, envía el recorte y abre la puerta | ESP-IDF 5.4 (C++), `espressif/esp32-camera`, `espressif/human_face_detect` (MSR + MNP, int8), esp-mqtt | A | `firmware/` |
| Simulador | Hace lo mismo que la cámara con la webcam o con una carpeta de fotos | Python 3.13, OpenCV (YuNet), httpx, paho-mqtt | A | `simulador/` |
| Servidor | Huella, reglas, inscripción, asistencia, eventos MQTT, API y web | Python 3.13, FastAPI, OpenCV (YuNet + SFace), SQLAlchemy 2, psycopg 3, pgvector, Alembic, paho-mqtt | B | `servidor/` |
| Servidor MCP | Herramientas de solo lectura del agente | SDK oficial `mcp` de Python, mismo paquete del servidor | B | `servidor/` |
| Base de datos | Personas, huellas, eventos y asistencia | PostgreSQL 18 + pgvector | B | `specs/contratos/base-de-datos.sql` |
| Broker MQTT | Mensajes entre servidor, cámara y Home Assistant | Mosquitto 2 | B | `infra/mosquitto/` |
| Home Assistant | Panel, automatizaciones (puerta y avisos) y Assist | Home Assistant Container | C | `homeassistant/` |
| Ollama | Modelo del agente | Ollama con qwen2.5:3b o qwen2.5:1.5b | C | `infra/` |
| Web | Administración: personas, inscripción, accesos, asistencia y cámaras | React + Vite + TypeScript, servida por el servidor | C | `web/` |

Modelos de cara del servidor (de `opencv/opencv_zoo`, se descargan al construir la imagen): `face_detection_yunet_2023mar.onnx` (YuNet, licencia MIT) y `face_recognition_sface_2021dec.onnx` (SFace, licencia Apache 2.0).

## Flujos

### Cada llegada (pasos 1 a 6)

1. La cámara toma una imagen, detecta la cara con ESP-DL y, si mide al menos `CARA_MIN_PX` de alto, la recorta con 25 % de margen, la comprime en JPEG y la envía por HTTP (máximo una por segundo).
2. El servidor valida el token de la cámara, vuelve a detectar la cara con YuNet para alinearla y saca la huella con SFace: 128 números normalizados.
3. Busca la muestra más parecida con pgvector y aplica las reglas R1 a R4. Si hay una inscripción activa en esa cámara, aplica R7 y R9 en su lugar.
4. Guarda el evento y, si es la primera entrada del día, la asistencia (R5). Responde a la cámara.
5. Publica el evento en MQTT. Home Assistant actualiza sus entidades y, si el acceso es permitido, su automatización publica `ABRIR`.
6. La cámara (o el simulador) abre la puerta 3 s con un LED o un relé y publica el estado de la puerta.

Un desconocido no recibe ni publica a quién se parece. Las repeticiones de R4 no guardan evento ni publican nada.

### Inscripción

1. El administrador crea la persona y registra su consentimiento en la web.
2. Abre una inscripción para esa persona en una cámara (por ejemplo, `entrada`).
3. La persona se para frente a la cámara. Cada cara que llega se revisa con R7 y las válidas se guardan como muestras. La web muestra el avance.
4. Con 5 muestras la inscripción se completa y la cámara vuelve a reconocer. Si pasan 120 s, vence (R9).

### Pregunta al agente (pasos A a C)

- A. Alguien escribe en Assist «¿quién llegó tarde hoy?».
- B. Home Assistant le pasa la pregunta y las herramientas de AccesIA a Ollama; el modelo pide `asistencia_del_dia`.
- C. Home Assistant llama al servidor MCP, que consulta las vistas con el usuario `agente`. El modelo responde con esos datos.

## Servicios de Docker Compose

Archivo principal: `infra/compose.yaml`. Home Assistant va en la red de Docker, no en modo host (D-19).

| Servicio | Imagen | Puerto interno | Publicado en el equipo | Quién lo usa |
| --- | --- | --- | --- | --- |
| `postgres` | `pgvector/pgvector:pg18` | 5432 | `127.0.0.1:${POSTGRES_PORT}` (5434 por defecto) | `servidor`, `mcp`, pruebas |
| `mosquitto` | `eclipse-mosquitto:2` | 1883 | `1883` en la red | `servidor`, cámara, simulador, Home Assistant |
| `servidor` | `accesia-servidor` (propia) | 8000 | `8000` en la red | cámara, simulador, web |
| `mcp` | `accesia-servidor` (misma imagen, otro comando) | 8001 | no se publica | Home Assistant |
| `homeassistant` | `ghcr.io/home-assistant/home-assistant:stable` | 8123 | `8123` en la red | navegador |
| `ollama` | `ollama/ollama` | 11434 | no se publica | Home Assistant |

- Volúmenes: `datos-postgres`, `datos-ollama` y `datos-mosquitto`. La configuración de Home Assistant se monta desde `homeassistant/config`.
- Las versiones exactas de las imágenes se fijan el Día 4, antes de armar el kit.
- Escenario 2 (Home Assistant OS en la Raspberry): `infra/compose.escenario2.yaml` quita `homeassistant` y publica `mcp` (8001) y `ollama` (11434) en la red del portátil, para que la Raspberry los alcance. Solo se usa en la red propia o en un hotspot.

Direcciones dentro de la red de Docker: `http://servidor:8000`, `http://mcp:8001/mcp`, `http://ollama:11434`, `mqtt://mosquitto:1883`.

## Configuración (`infra/.env`)

`infra/.env` no se sube a Git. `infra/.env.example` lleva los mismos nombres sin claves. Compose arma con estas variables `DATABASE_URL` y `MQTT_URL` para el servidor.

| Variable | Ejemplo | Para qué |
| --- | --- | --- |
| `POSTGRES_PORT` | `5434` | Puerto de PostgreSQL en el equipo (no se usa 5432, ver `CLAUDE.md`) |
| `POSTGRES_DB` | `accesia` | Nombre de la base |
| `POSTGRES_USER` | `accesia` | Dueño de la base, lo usa el servidor |
| `POSTGRES_PASSWORD` | (clave) | Clave del dueño |
| `AGENTE_DB_PASSWORD` | (clave) | Clave del usuario `agente`, de solo lectura (D-15) |
| `SESION_SECRETO` | (64 caracteres al azar) | Firma de la cookie de sesión de la web |
| `ADMIN_CORREO` | `admin@accesia.local` | Primer administrador, creado al arrancar si no existe |
| `ADMIN_CLAVE_INICIAL` | (clave) | Clave inicial de ese administrador |
| `MQTT_SERVIDOR_CLAVE` | (clave) | Usuario MQTT `servidor` |
| `MQTT_HA_CLAVE` | (clave) | Usuario MQTT `homeassistant` |
| `MQTT_CAMARA_CLAVE` | (clave) | Usuario MQTT `camara` (cámara y simulador) |
| `UMBRAL_SIMILITUD` | `0.363` | R1 |
| `VENTANA_REPETIDO_S` | `60` | R4 |
| `ALERTA_DESCONOCIDOS` | `3` | R6 |
| `ALERTA_VENTANA_S` | `60` | R6 |
| `INSCRIPCION_MUESTRAS` | `5` | R9 |
| `INSCRIPCION_VENCE_S` | `120` | R9 |
| `CARA_MIN_PX` | `80` | R7 y envío de la cámara |
| `NITIDEZ_MIN` | `60` | R7 |
| `ZONA_HORARIA` | `America/Bogota` | R8 |
| `OLLAMA_MODELO` | `qwen2.5:3b` | Modelo que se descarga para el agente (D-06) |

## Firmware de la cámara

### Perfiles de placa

Cada perfil es un binario. Los pines salen de la documentación oficial de cada placa y el código cita la fuente. La PSRAM esperada se confirma con el firmware de diagnóstico.

| Perfil | Placa | PSRAM esperada |
| --- | --- | --- |
| `esp32s3_eye` | ESP32-S3-EYE (Espressif) | octal |
| `freenove_s3_cam` | Freenove ESP32-S3 WROOM CAM | octal |
| `xiao_s3_sense` | Seeed Studio XIAO ESP32S3 Sense | octal |
| `generico_octal` | Otra ESP32-S3 con cámara; pines por consola | octal |
| `generico_quad` | Otra ESP32-S3 con cámara; pines por consola | quad (D-17) |

Binarios auxiliares:

- `diagnostico`: muestra por el monitor serial el chip, la flash, la PSRAM y el sensor de la cámara. En clase dice en un minuto qué perfil usar.
- `respaldo`: servidor de imágenes al estilo CameraWebServer (`GET /capture`). Lo usa el modo extraer del servidor (RF-10 · C4).

La tabla de particiones cabe en 4 MB de flash, para que el mismo binario sirva en placas de 4, 8 y 16 MB.

### Configuración por consola serial

Se guarda en NVS y no requiere recompilar. Comandos:

| Comando | Ejemplo |
| --- | --- |
| `estado` | Muestra perfil, Wi-Fi, IP, servidor, MQTT y PSRAM |
| `wifi <ssid> <clave>` | `wifi AccesIA clave123` |
| `servidor <url>` | `servidor http://10.42.0.1:8000` |
| `codigo <codigo>` | `codigo entrada` |
| `token <token>` | El token que da la web al crear la cámara |
| `mqtt <url> <usuario> <clave>` | `mqtt mqtt://10.42.0.1:1883 camara clave123` |
| `perfil <nombre>` | `perfil generico_octal` |
| `pin <nombre> <número>` | `pin xclk 15` (solo perfiles genéricos) |
| `puerta <pin> <segundos>` | `puerta 2 3`; `-1` si no hay LED ni relé |
| `cara_min <px>` | `cara_min 80` (igual que `CARA_MIN_PX` del servidor) |
| `reiniciar` | Reinicia la placa |
| `ayuda` | Lista los comandos |

### Comportamiento

- Captura en QVGA (320 × 240) para detectar; recorta la cara más grande con 25 % de margen y la envía en JPEG de calidad 80.
- Envía como máximo un recorte por segundo. Tras `permitido`, `denegado` o `desconocido` espera 3 s antes de volver a enviar.
- Si el servidor no responde (tiempo de espera 5 s), reintenta con espera creciente de 1, 2, 4 y hasta 10 s, y lo muestra por el monitor serial.
- MQTT: se suscribe a `accesia/{codigo}/puerta/set`, publica el estado de la puerta, su estado general cada 60 s y su disponibilidad con último deseo (`contratos/mqtt.md`).

## Simulador

- Cumple `contratos/api-dispositivo.md` y la parte de la cámara en `contratos/mqtt.md`.
- Dos modos: webcam (detecta con YuNet, recorta con el mismo margen y envía) y carpeta de fotos de `datos/` (para pruebas repetibles).
- Simula la puerta: al recibir `ABRIR` muestra «PUERTA ABIERTA» 3 s y publica su estado.
- Se registra como un dispositivo de tipo `simulador`.

## Red y despliegue

- Red propia: la Raspberry crea el Wi-Fi «AccesIA» y queda en `10.42.0.1`. La cámara apunta a `http://10.42.0.1:8000` y a `mqtt://10.42.0.1:1883`.
- Plan B de red: la red del salón o el hotspot de un celular; la cámara se reconfigura por consola serial.

| Escenario | Qué trae la Raspberry | Dónde corre cada cosa |
| --- | --- | --- |
| 1 | Raspberry Pi OS | Todo en la Raspberry con `infra/compose.yaml` |
| 2 | Home Assistant OS | Home Assistant en la Raspberry (se restaura nuestra copia de seguridad); el resto en un portátil con `compose.escenario2.yaml` |
| 3 | Nada | Raspberry Pi OS en una memoria USB y se sigue como en el escenario 1. Pi 5: arranca desde USB sin configurar nada; Pi 4: solo si su bootloader ya lo permite |

Si la Raspberry tiene 2 GB o menos, Home Assistant queda en la Raspberry y el resto en un portátil. Los pasos completos están en `docs/guia-dia-de-clase.md`.
