<!--
Nombre: arquitectura.md
Descripción: Piezas de AccesIA, flujos, servicios, puertos, configuración, firmware y despliegue.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.8
-->

# Arquitectura

**La cámara ve, el servidor reconoce, Home Assistant actúa y el agente responde.** Todo, menos la cámara, corre con Docker Compose en la Raspberry Pi (o en un portátil, según el escenario). En la demo (D-21), Docker Compose corre en un portátil y la Raspberry Pi 5 trae Home Assistant OS (escenario 2).

Los diagramas están en `docs/diagramas/`: `arquitectura-explicada.html` (quién hace qué) y `paso-a-paso.html` (el recorrido).

## Piezas

| Pieza | Qué hace | Tecnología | Frente | Carpeta |
| --- | --- | --- | --- | --- |
| Cámara | Detecta la cara y envía el recorte. Hasta que llegue el módulo de cámara (D-21) la hace el simulador; el firmware del ESP32-S3 queda como referencia (PR #7) | ESP-IDF 5.4 (C++), `espressif/esp32-camera`, `espressif/human_face_detect` (MSR + MNP, int8), esp-mqtt | A | `firmware/` |
| Placa del punto de acceso | Abre la puerta (un LED), publica su estado y un sensor de temperatura y humedad; la cámara, cuando llegue el módulo (D-21) | Seeed Studio XIAO ESP32-C6, ESP-IDF 5.4 (C++), esp-mqtt, `esp-idf-lib/dht` | A | `firmware/` |
| Simulador | Hace lo mismo que la cámara con la webcam o con una carpeta de fotos | Python 3.13, OpenCV (YuNet), httpx, paho-mqtt | A | `simulador/` |
| Servidor | Huella, reglas, inscripción, asistencia, eventos MQTT, API y web | Python 3.13, FastAPI, OpenCV (YuNet + SFace), SQLAlchemy 2, psycopg 3, pgvector, Alembic, paho-mqtt | B | `servidor/` |
| Servidor MCP | Herramientas de solo lectura del agente | SDK oficial `mcp` 2.x de Python (`MCPServer`, que en la 1.x se llamaba FastMCP), mismo paquete del servidor | B | `servidor/` |
| Base de datos | Personas, huellas, eventos y asistencia | PostgreSQL 18 + pgvector | B | `specs/contratos/base-de-datos.sql` |
| Broker MQTT | Mensajes entre servidor, cámara, placa y Home Assistant | Mosquitto 2, en el portátil en la demo (D-21) | B | `infra/mosquitto/` |
| Home Assistant | Panel, automatizaciones (puerta y avisos) y Assist | Home Assistant OS en la Raspberry Pi 5 (D-21); Home Assistant Container en el escenario 1 | C | `homeassistant/` |
| Ollama | Modelo del agente | Ollama con qwen2.5:3b o qwen2.5:1.5b | C | `infra/` |
| Web | Administración: personas, inscripción, accesos, asistencia, cámaras y horarios | React + Vite + TypeScript, servida por el servidor | C | `web/` |

Modelos fijos, los mismos en el simulador y en el servidor. Se descargan de un commit fijo de `opencv/opencv_zoo` y se comprueban con su SHA-256; en el PC quedan en `datos/modelos/`, que Git y Docker ignoran:

| Modelo | Commit de `opencv/opencv_zoo` | SHA-256 | Bytes |
| --- | --- | --- | --- |
| `face_detection_yunet_2023mar.onnx` | `48b10fa505aeb51fbd127fc60a5c660040e823b7` | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | 232 589 |
| `face_recognition_sface_2021dec.onnx` | `48b10fa505aeb51fbd127fc60a5c660040e823b7` | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` | 38 696 353 |

- URL de YuNet: `https://github.com/opencv/opencv_zoo/raw/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_detection_yunet/face_detection_yunet_2023mar.onnx`.
- URL de SFace, que solo usa el servidor: `https://github.com/opencv/opencv_zoo/raw/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_recognition_sface/face_recognition_sface_2021dec.onnx`.
- Licencias: YuNet, MIT; SFace, Apache 2.0.
- opencv_zoo guarda los modelos con Git LFS: `raw.githubusercontent.com` devuelve el puntero de LFS y no el modelo. La URL de `github.com/…/raw/…` redirige al modelo.
- YuNet 2023mar pide OpenCV 4.8 o más reciente. El simulador usa `opencv-python` 4.14.0.94, la última 4.x estable; el servidor, `opencv-python-headless` 4.14.0.94, la misma versión sin ventanas.
- En el servidor:
  - en el PC y en la CI los baja `uv run accesia descargar-modelos` (desde `servidor/`) a `datos/modelos/`, desde la raíz del repositorio;
  - la imagen los baja al construir, a `/app/datos/modelos`, y si el tamaño o el SHA-256 no coinciden, la construcción falla;
  - se cargan una vez, al arrancar; sin ellos, el servidor no arranca.

## Flujos

### Cada llegada (pasos 1 a 6)

1. La cámara toma una imagen, detecta la cara con ESP-DL y, si mide al menos `CARA_MIN_PX` de alto, la recorta con 25 % de margen (fórmula en `contratos/api-dispositivo.md`), la comprime en JPEG y la envía por HTTP. Antes de enviar otra espera al menos 1 s desde la respuesta.
2. El servidor valida el token de la cámara, vuelve a detectar la cara con YuNet para alinearla y saca la huella con SFace: 128 números normalizados.
3. Busca la muestra más parecida con pgvector y aplica las reglas R1 a R4. Si hay una inscripción activa en esa cámara, aplica R7 y R9 en su lugar.
4. Guarda el evento y, si es la primera entrada permitida del día y la persona aún no tiene llegada, la asistencia (R5). Responde a la cámara.
5. Publica el evento en MQTT, después de confirmar la transacción y solo si está conectado al broker: sin conexión lo descarta, para que un `permitido` viejo no abra la puerta al reconectarse. Home Assistant actualiza sus entidades y, si el acceso es permitido, su automatización publica `ABRIR`.
6. La cámara (o el simulador) abre la puerta 3 s con un LED o un relé y publica el estado de la puerta.

Un desconocido no recibe ni publica a quién se parece. Las repeticiones de R4 no guardan evento: la de un `permitido` se publica con `repetido: true` para que la puerta se abra otra vez, y la de un `denegado` no publica nada.

Con el hardware de D-21, el paso 1 lo hace el simulador hasta que llegue el módulo de cámara, y el paso 6 lo hace la placa con su LED.

### Llegada registrada a mano

Si la persona no dio consentimiento, o si la cámara falla, un administrador registra su llegada en la pantalla Asistencia (RF-06 · C5). El servidor aplica R5 a la hora dada, guarda la asistencia con origen `manual` y publica el resumen en MQTT. No hay evento de acceso ni se abre la puerta.

### Inscripción

1. El administrador crea la persona y registra su consentimiento en la web.
2. Abre una inscripción para esa persona en una cámara (por ejemplo, `entrada`).
3. La persona se para frente a la cámara. Cada cara que llega se revisa con R7 (desde la segunda, también que se parezca a la primera muestra) y las válidas se guardan como muestras. La web muestra el avance.
4. Con 5 muestras la inscripción se completa y la cámara vuelve a reconocer. Si pasan 120 s, vence (R9).

### Pregunta al agente (pasos A a C)

- A. Alguien escribe en Assist «¿quién llegó tarde hoy?».
- B. Home Assistant le pasa la pregunta y las herramientas de AccesIA a Ollama; el modelo pide `asistencia_del_dia`.
- C. Home Assistant llama al servidor MCP, que consulta las vistas con el usuario `agente`. El modelo responde con esos datos.

### Temperatura y humedad (D-21)

1. Cada 30 s la placa lee su sensor (DHT22 o DHT11) y publica la temperatura y la humedad en `accesia/{codigo}/ambiente`.
2. Home Assistant las muestra en el dispositivo de la cámara. El descubrimiento de esos dos sensores lo publica la placa al conectarse, así que no depende del servidor.
3. Si la placa se apaga, su último deseo deja las dos entidades no disponibles.

## Servicios de Docker Compose

Archivo principal: `infra/compose.yaml`. Home Assistant va en la red de Docker, no en modo host (D-19).

| Servicio | Imagen | Puerto interno | Publicado en el equipo | Quién lo usa |
| --- | --- | --- | --- | --- |
| `postgres` | `pgvector/pgvector:pg18` | 5432 | `127.0.0.1:${POSTGRES_PORT}` (5434 por defecto) | `servidor`, `mcp`, pruebas |
| `mosquitto` | `eclipse-mosquitto:2` | 1883 | `1883` en la red | `servidor`, placa, simulador, Home Assistant |
| `servidor` | `accesia-servidor` (propia, `servidor/Dockerfile` con la raíz del repositorio como contexto) | 8000 | `8000` en la red | cámara, simulador, web |
| `mcp` | `accesia-servidor` (misma imagen, comando `accesia mcp`) | 8001 | no se publica | Home Assistant |
| `homeassistant` | `ghcr.io/home-assistant/home-assistant:stable` | 8123 | `8123` en la red | navegador |
| `ollama` | `ollama/ollama` | 11434 | no se publica | Home Assistant |

- Volúmenes: `datos-postgres`, `datos-ollama` y `datos-mosquitto`. `datos-postgres` se monta en `/var/lib/postgresql`: PostgreSQL 18 guarda los datos en `/var/lib/postgresql/18/docker`, no en `/var/lib/postgresql/data`. La configuración de Home Assistant se monta desde `homeassistant/config`.
- La imagen del servidor se construye con la raíz del repositorio como contexto, para copiar `specs/contratos/base-de-datos.sql`, el texto de `specs/consentimiento.md` y, más adelante, la web compilada. Un `.dockerignore` en la raíz deja fuera `datos/`, `kit/` y `node_modules/`.
- El servidor corre con un solo proceso de Uvicorn: la hora de la última alerta de R6, el control del 429 y la conexión MQTT viven en memoria, y con varios procesos cada uno contaría por su lado.
- Las versiones exactas de las imágenes se fijan el Día 4, antes de armar el kit.
- Escenario 2 (Home Assistant OS en la Raspberry), el de la demo (D-21): `infra/compose.escenario2.yaml` quita `homeassistant` y publica `mcp` (8001) y `ollama` (11434) en la red del portátil, para que la Raspberry los alcance. Solo se usa en el hotspot del portátil o en otra red propia. Era la excepción a D-16 y D-19; con D-21 es el caso normal.
- Ollama en el portátil (RNF-03 · C3): `infra/compose.ollama-portatil.yaml` levanta solo `ollama` en el portátil y publica el 11434 en la red propia; Home Assistant sigue en la Raspberry. Lo crea la tarea C del Día 4. Es otra excepción a D-19.
- El servicio `mcp` no recibe `infra/.env`: Compose le arma `DATABASE_URL` con el usuario `agente` y `AGENTE_DB_PASSWORD`, y le pasa `ZONA_HORARIA` y `MCP_HOSTS_PERMITIDOS`. Así nunca tiene la clave del dueño de la base (D-15).

Direcciones dentro de la red de Docker: `http://servidor:8000`, `http://mcp:8001/mcp`, `http://ollama:11434`, `mqtt://mosquitto:1883`.

## Configuración (`infra/.env`)

`infra/.env` no se sube a Git. `infra/.env.example` lleva los mismos nombres sin claves. Compose arma con estas variables `DATABASE_URL` y `MQTT_URL` para el servidor, y la `DATABASE_URL` del usuario `agente` para `mcp`.

| Variable | Ejemplo | Para qué |
| --- | --- | --- |
| `POSTGRES_PORT` | `5434` | Puerto de PostgreSQL en el equipo (no se usa 5432, ver `CLAUDE.md`). Si Windows también tiene reservado este, se elige otro (`infra/README.md`) |
| `POSTGRES_DB` | `accesia` | Nombre de la base |
| `POSTGRES_USER` | `accesia` | Dueño de la base, lo usa el servidor |
| `POSTGRES_PASSWORD` | (clave) | Clave del dueño |
| `AGENTE_DB_PASSWORD` | (clave) | Clave del usuario `agente`, de solo lectura (D-15) |
| `SESION_SECRETO` | (64 caracteres al azar) | Firma de la cookie de sesión de la web. Sin ella el servidor no arranca. La sesión dura 8 horas desde el último uso |
| `ADMIN_CORREO` | `admin@example.com` | Primer administrador, creado al arrancar si no existe, con el nombre «Administrador». Con dominio no reservado: la validación de correos rechaza `.local`, `.test` o `.localhost` |
| `ADMIN_CLAVE_INICIAL` | (clave) | Clave inicial de ese administrador, de al menos 8 caracteres. Si el administrador ya existe, no se toca su clave |
| `MQTT_SERVIDOR_CLAVE` | (clave) | Usuario MQTT `servidor` |
| `MQTT_HA_CLAVE` | (clave) | Usuario MQTT `homeassistant` |
| `MQTT_CAMARA_CLAVE` | (clave) | Usuario MQTT `camara` (cámara y simulador) |
| `UMBRAL_SIMILITUD` | `0.363` | R1 |
| `VENTANA_REPETIDO_S` | `60` | R4 |
| `ALERTA_DESCONOCIDOS` | `3` | R6 |
| `ALERTA_VENTANA_S` | `60` | R6 |
| `INSCRIPCION_MUESTRAS` | `5` | R9 |
| `INSCRIPCION_VENCE_S` | `120` | R9 |
| `CARA_MIN_PX` | `80` | Envío de la cámara; el servidor descarta por debajo de 0,8 × este valor (R7) |
| `NITIDEZ_MIN` | `60` | R7 |
| `ZONA_HORARIA` | `America/Bogota` | R8 |
| `OLLAMA_MODELO` | `qwen2.5:3b` | Modelo que se descarga para el agente (D-06) |
| `MCP_HOSTS_PERMITIDOS` | `192.168.137.1:8001` | Encabezados `Host` que acepta el servidor MCP además de `mcp:8001`, separados por comas. En el escenario 2 (D-21), la IP del portátil en el hotspot. Si falta, Compose usa `192.168.137.1:8001` |

## Firmware

### Placa de la demo: XIAO ESP32-C6 (D-21)

Un solo binario para la Seeed Studio XIAO ESP32-C6: 4 MB de flash, 512 KB de SRAM y sin PSRAM. La tabla de particiones de 4 MB no cambia. Todavía no tiene cámara: maneja la puerta, publica su estado y lee un sensor de temperatura y humedad.

| Uso | Pin | Nota |
| --- | --- | --- |
| Sensor DHT22 o DHT11 (DATA) | D2 = GPIO2 | El módulo de tres pines trae su resistencia de pull-up |
| Conmutador de antena | GPIO3 | En bajo al arrancar, antes del Wi-Fi: enciende el conmutador. ESP-IDF no lo hace solo |
| Antena | GPIO14 | En bajo, la cerámica interna (por defecto); en alto, una externa U.FL |
| LED de usuario | GPIO15 | Enciende en bajo. Hace de puerta y muestra el estado |
| UART0 | GPIO16 (TX) y GPIO17 (RX) | La consola lee por UART0 y por el USB-C (USB Serial/JTAG) |

Los pines salen de la wiki de Seeed (`wiki.seeedstudio.com/xiao_esp32c6_getting_started`) y se verifican con la placa. La wiki no dice en qué nivel enciende el LED.

Comportamiento:

- Al arrancar pone GPIO3 en bajo y GPIO14 según la antena configurada, y después enciende el Wi-Fi en 2,4 GHz.
- MQTT, con su código como client id (la ACL lo exige):
  - se suscribe a `accesia/{codigo}/puerta/set`;
  - publica la puerta, su estado general cada 60 s y su disponibilidad con último deseo;
  - publica las lecturas de ambiente cada 30 s y el descubrimiento de sus dos sensores (`contratos/mqtt.md`).
- La puerta manda sobre el LED. Con `ABRIR` queda encendido los segundos configurados (3 por defecto), y la placa publica `abierta` y luego `cerrada`; `CERRAR` lo apaga antes. El resto del tiempo el LED muestra el estado de la placa: parpadea mientras se conecta al Wi-Fi o al broker.
- Sensor: DHT22 por defecto; el comando `sensor` lo cambia. Tras 3 lecturas fallidas seguidas publica `null`.

### Consola serial

Se guarda en NVS y no requiere recompilar. Los comandos entran por UART0 y por el USB nativo.

| Comando | Ejemplo |
| --- | --- |
| `estado` | Muestra la placa, el Wi-Fi, la IP, el servidor, MQTT, el sensor con su última lectura y la antena |
| `wifi <ssid> <clave>` | `wifi AccesIA clave123` (el hotspot del portátil) |
| `servidor <url>` | `servidor http://192.168.137.1:8000` |
| `codigo <codigo>` | `codigo entrada` |
| `token <token>` | El token que da la web al crear la cámara |
| `mqtt <url> <usuario> <clave>` | `mqtt mqtt://192.168.137.1:1883 camara clave123` |
| `puerta <pin> <segundos> [bajo\|alto]` | `puerta 15 3 bajo`, lo de fábrica en el C6. El nivel es el que enciende; `-1` si no hay LED ni relé |
| `sensor <dht22\|dht11>` | `sensor dht11` |
| `antena <interna\|externa>` | `antena externa` |
| `reiniciar` | Reinicia la placa |
| `ayuda` | Lista los comandos |

Los valores de fábrica apuntan al portátil en el hotspot: servidor `http://192.168.137.1:8000` y MQTT `mqtt://192.168.137.1:1883` con el usuario `camara`. Los comandos `perfil`, `pin` y `cara_min` son del firmware del ESP32-S3 y vuelven con él.

### Cámara

Así se comporta cualquier cámara que envíe recortes (hoy el simulador; el ESP32-S3 de referencia):

- Captura en QVGA (320 × 240) para detectar; recorta la cara más grande (la de mayor área) con la fórmula de `contratos/api-dispositivo.md` y la envía en JPEG de calidad 80.
- Después de cada respuesta espera al menos 1 s, contado desde que la recibe, antes de enviar otro recorte. Tras `permitido`, `denegado` o `desconocido` espera 3 s.
- Si el servidor no responde (tiempo de espera 5 s), reintenta con espera creciente de 1, 2, 4 y hasta 10 s, y lo muestra por el monitor serial.

#### Cuando llegue el módulo de cámara

El firmware del C6 deja un punto de extensión, sin código de cámara ni de TinyML: una fuente de cuadros y un detector. Lo que se haga depende del módulo:

- **Cámara SPI con salida JPEG conectada al C6:**
  - Un cuadro QVGA en JPEG (10 a 20 KB) cabe en la SRAM.
  - ESP-DL no trae modelos de caras para el C6 y, sin PSRAM, no cabrían. El TinyML sería un clasificador int8 de TensorFlow Lite Micro (`espressif/esp-tflite-micro`, como su ejemplo `person_detection`, de 96 × 96 en grises). Dice si hay alguien, pero no dónde está la cara.
  - Sin cajas, el C6 no puede recortar ni medir `cara_min`. Enviaría el cuadro completo, y el servidor lo trataría como en el modo extraer: YuNet, la cara de mayor área, la misma fórmula y `CARA_MIN_PX`.
  - Esa parte del servidor ya existe: `recortar_cara_mas_grande` en `servidor/accesia/vision.py` (tarea B2) detecta con YuNet, elige la cara de mayor área y recorta con la fórmula del contrato; se prueba con `casos-recorte.json`.
  - Eso cambia `api-dispositivo.md` y `openapi.yaml`, en su propio PR.
- **Placa con cámara aparte:**
  - Si es un ESP32-S3 con cámara, vuelve el firmware de referencia y el contrato no cambia.
  - Si es un ESP32-CAM, sirve como cámara de respaldo, con el modo extraer.

#### Referencia: ESP32-S3 (PR #7)

El firmware del ESP32-S3 del enunciado quedó en el PR #7, en borrador, por si se vuelve a él. Detecta con `espressif/human_face_detect` (MSR + MNP, int8), recorta, y su consola suma `perfil`, `pin` y `cara_min`. Puede volver como otro target del mismo proyecto (`idf.py set-target esp32s3`). Para él valen D-17 y esta tabla:

| Perfil | Placa | PSRAM esperada | Binario |
| --- | --- | --- | --- |
| `esp32s3_eye` | ESP32-S3-EYE (Espressif) | octal | `octal` |
| `freenove_s3_cam` | Freenove ESP32-S3 WROOM CAM | octal | `octal` |
| `xiao_s3_sense` | Seeed Studio XIAO ESP32S3 Sense | octal | `octal` |
| `generico_octal` | Otra ESP32-S3 con cámara; pines por consola | octal | `octal` |
| `generico_quad` | Otra ESP32-S3 con cámara; pines por consola | quad | `quad` |

Sus binarios auxiliares, `diagnostico` (chip, flash, PSRAM y sensor de cualquier placa) y `respaldo` (`GET /capture` para el modo extraer, RF-10 · C4), quedan para cuando vuelva el S3 o llegue un ESP32-CAM.

## Simulador

- Cumple `contratos/api-dispositivo.md` y la parte de la cámara en `contratos/mqtt.md`, con su código como client id. No puede estar conectado a la vez que una cámara con el mismo código.
- Dos modos: webcam (detecta con YuNet, recorta con la misma fórmula y envía) y carpeta de fotos de `datos/` (para pruebas repetibles). Los dos pasan los casos de `contratos/casos-recorte.json`.
- Modo «como la cámara», que se combina con los dos anteriores: reduce cada imagen a 320 × 240 y la comprime en JPEG de calidad 80 antes de detectar, para que los recortes se parezcan a los del ESP32-S3. Se usa para calibrar el umbral (RNF-07).
  - Una imagen que no es 4:3 se recorta primero al centro, al rectángulo 4:3 más grande, y después se reduce. Así la cara no se deforma y la escala es la misma en los dos ejes.
  - Ejemplo: una webcam de 1280 × 720 (16:9) pasa a 960 × 720, perdiendo 160 px de cada lado, y después a 320 × 240.
  - Una foto vertical pierde arriba y abajo: las fotos del modo carpeta se toman horizontales.
- Simula la puerta: al recibir `ABRIR` muestra «PUERTA ABIERTA» 3 s y publica su estado.
- Se registra como un dispositivo de tipo `simulador`.

## Red y despliegue

- Red de la demo (D-21): el hotspot de Windows del portátil, en 2,4 GHz, porque el C6 no usa 5 GHz. El portátil queda en una IP que no cambia, que suele ser `192.168.137.1`: la placa apunta a `http://192.168.137.1:8000` y a `mqtt://192.168.137.1:1883`, y Home Assistant OS se conecta al broker en esa dirección. El firewall de Windows tiene que dejar entrar, en esa red, el 1883 (MQTT) y los puertos que usa la Pi: el 8001 (`mcp`) y el 11434 (`ollama`).
- Escenario 1: la Raspberry crea el Wi-Fi «AccesIA» en 2,4 GHz (`band bg` en NetworkManager) y queda en `10.42.0.1`.
- Plan B de red: la red del salón o el hotspot de un celular; la placa se reconfigura por consola serial.

| Escenario | Qué trae la Raspberry | Dónde corre cada cosa |
| --- | --- | --- |
| 1 | Raspberry Pi OS | Todo en la Raspberry con `infra/compose.yaml` |
| 2 | Home Assistant OS | Home Assistant en la Raspberry (se restaura nuestra copia de seguridad); el resto en un portátil con `compose.escenario2.yaml`. Es el de la demo (D-21) |
| 3 | Nada | Raspberry Pi OS en una memoria USB y se sigue como en el escenario 1. Pi 5: arranca desde USB sin configurar nada; Pi 4: solo si su bootloader ya lo permite |

Si la Raspberry tiene 2 GB o menos, Home Assistant queda en la Raspberry y el resto en un portátil. Los pasos completos están en `docs/guia-dia-de-clase.md`.
