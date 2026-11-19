<!--
Nombre: arquitectura.md
Descripción: Piezas de AccesIA, flujos, servicios, puertos, configuración, firmware y despliegue.
Fecha de creación: 2026-11-11
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 1.14
-->

# Arquitectura

**La cámara ve, el servidor reconoce, Home Assistant actúa y el agente responde.** En la demo (D-22), todo, menos la cámara y la placa, corre en la Raspberry Pi 5 como complementos de Home Assistant OS. En el portátil, Docker Compose levanta las mismas piezas para desarrollar y como plan B.

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
| Broker MQTT | Mensajes entre servidor, cámara, placa y Home Assistant | Mosquitto 2: en la demo, el complemento oficial de Home Assistant OS en la Pi (D-22); en el portátil, el de Compose | B | `infra/mosquitto/` |
| Home Assistant | Panel, automatizaciones (puerta y avisos) y Assist | Home Assistant OS en la Raspberry Pi 5 (D-21); Home Assistant Container en el escenario 1 | C | `homeassistant/` |
| Ollama | Modelo del agente | Ollama con `qwen2.5`, del tamaño que permita la RAM (D-06); en la demo, el complemento de SirUli en la Pi (D-22) | C | `infra/` |
| Web | Administración: personas, inscripción, accesos, asistencia, cámaras y horarios | React + Vite + TypeScript, servida por el servidor | C | `web/` |
| Complementos | Empaquetan la base y el servidor para Home Assistant OS (D-22) | `config.yaml` y `Dockerfile` de cada uno, que Supervisor construye en la Pi | B | `complementos/` |

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

## Complementos de Home Assistant OS (D-22)

En la demo, todo menos la cámara y la placa corre en la Raspberry Pi 5 como complementos (apps) de Home Assistant OS. Supervisor los arranca, los reinicia si fallan y los incluye en las copias de seguridad.

| Complemento | De quién | Nombre en la red interna | Publicado en la red del hotspot | Datos |
| --- | --- | --- | --- | --- |
| `accesia_base` | Nuestro, local | `local-accesia-base:5432` | Nada | `/data/postgres` |
| `accesia_servidor` | Nuestro, local | `local-accesia-servidor`: 8000 (API y web) y 8001 (MCP) | El 8000, para la placa, el simulador y el navegador | Nada propio; sus opciones quedan en `/data/options.json` |
| Mosquitto (`core_mosquitto`) | Oficial | `core-mosquitto:1883` | El 1883, para la placa y el simulador | La ACL, en `/share/mosquitto/` |
| Ollama | Comunidad (SirUli) | `<hash>-ollama:11434` | Nada | Los modelos, en `/share/ollama` |

- **Nombres.** Supervisor registra cada complemento en su DNS interno: los locales como `local-<slug>`, con `-` en lugar de `_`; el Mosquitto oficial como `core-mosquitto`; y los de un repositorio de la comunidad con el prefijo de ese repositorio, como `<hash>-ollama`. El nombre exacto sale en la página de cada complemento.
- **Quién llama a quién:**
  - el servidor usa `local-accesia-base:5432` y `core-mosquitto:1883`, con el usuario MQTT `servidor`;
  - Home Assistant se conecta solo a MQTT, con su usuario reservado `homeassistant`. Llega al MCP en `http://local-accesia-servidor:8001/mcp` y a Ollama en `http://<hash>-ollama:11434`;
  - la placa y el simulador usan la IP fija de la Pi en el hotspot: `http://<IP de la Pi>:8000` y `mqtt://<IP de la Pi>:1883`.
- **Lo que no se publica.** El MCP y Ollama solo están en la red interna, así que D-16 se cumple sin excepción. El `config.yaml` de `accesia_servidor` publica solo el 8000. El complemento de Ollama publica el 11434 por defecto: se desactiva en su sección Red.
- **La web** va en la raíz del puerto 8000 (`http://<IP de la Pi>:8000/`), sin Ingress, igual que en el portátil.
- **`accesia_base`.** Su `Dockerfile` parte de `pgvector/pgvector:pg18` y suma `jq`. Un `run.sh` lee las claves de `/data/options.json` y arranca PostgreSQL con `PGDATA=/data/postgres`.
- **`accesia_servidor`.** Es la imagen del servidor, adaptada. Su `run.sh`:
  - lee las opciones y deja `/data/options.json` legible solo para root;
  - espera la base y corre la migración;
  - arranca Uvicorn en el 8000 con el usuario `accesia`, y `accesia mcp` en el 8001 con el usuario `agente` y un entorno limpio: solo la `DATABASE_URL` del usuario `agente` y `MCP_HOSTS_PERMITIDOS=local-accesia-servidor:8001`. Así el MCP nunca tiene las claves del dueño de la base, como en el Compose (D-15);
  - termina si uno de los dos falla, para que Supervisor lo reinicie con el Watchdog.
- **Comandos en la Pi.** Las cámaras se crean en la web (RF-10 · C1). `semilla agente`, con `--con-datos-reales` o `--borrar`, entra por la entrada estándar del complemento, con la acción `hassio.app_stdin`; `run.sh` solo acepta esos tres textos.
- **Mosquitto.** `servidor` y `camara` van en sus `logins`. Con `customize` activo y la carpeta `mosquitto`, lee `/share/mosquitto/acl.conf`, que tiene una sola línea: `acl_file /share/mosquitto/accesscontrollist`. Ese archivo es la ACL de `contratos/mqtt.md`, la misma de `infra/mosquitto/acl`.
- **Ollama.** El complemento de SirUli usa la imagen oficial `ollama/ollama` (la 0.40.16 en noviembre de 2026), para aarch64 y amd64. Trae `OLLAMA_KEEP_ALIVE=-1`, así que el modelo queda cargado en memoria, y `OLLAMA_NUM_PARALLEL=1`: un solo espacio de caché, el que reutiliza el comienzo del prompt. Con sus valores por defecto, `OLLAMA_KV_CACHE_TYPE=q8_0` y `OLLAMA_FLASH_ATTENTION=0`, Ollama 0.40.16 no carga el modelo («quantized V cache requires flash_attn to be enabled»): se cambia `OLLAMA_FLASH_ATTENTION` a 1 en las opciones del complemento. Así se comprobó en el portátil, solo con CPU. Como el complemento es «legacy», Supervisor le pasa sus opciones como variables de entorno.
- **Construcción.** Sin `image` en su `config.yaml`, la Pi construye cada complemento local desde su `Dockerfile`. Desde Supervisor 2026.04 ya no llega `BUILD_FROM`, así que cada `Dockerfile` lleva su `FROM` explícito; `build.yaml` está obsoleto.
- **Empaquetado.** Supervisor solo ve la carpeta del complemento. Por eso `scripts/empaquetar-complementos.ps1` arma `kit/complementos/`, que Git ignora, con:
  - el código del servidor;
  - el SQL del contrato y `consentimiento.md`;
  - la web compilada;
  - los modelos de cara, para no bajarlos en la Pi.
- **Instalación:**
  1. Con el complemento Samba share, copiar las dos carpetas a `\\<IP de la Pi>\addons\`.
  2. En la tienda de complementos: ⋮ → «Buscar actualizaciones» → «Complementos locales» → Instalar. La Pi construye la imagen.
  3. Poner las claves y las reglas en las opciones de cada complemento.
  4. Arrancar primero la base y después el servidor.

  Construir necesita internet una vez: las imágenes base y los paquetes de Python. Si la Pi solo está disponible en clase, se instala allá con el internet del celular. Los archivos del modelo de Ollama van en el kit y se copian por Samba a `/share/ollama`, sin internet.
- **Configuración.** En la Pi, las variables de `infra/.env` pasan a las opciones de los complementos (D-14): se cambian en la interfaz de Home Assistant y se reinicia el complemento. Las claves son del tipo `password`, que la interfaz muestra oculto. La lista está en `complementos/accesia_servidor/DOCS.md`. `infra/.env` sigue para el portátil.
- **Copias de seguridad.** Incluyen `/data` de `accesia_base`, es decir, las huellas: van siempre cifradas y nunca al repositorio, y la del kit se toma sin inscripciones (`modelo-datos.md`, Retención).

### Presupuesto de RAM

Son estimaciones. Las del servidor y el MCP se midieron en el portátil, con los procesos de Python; las de los modelos son de una Pi 5 con Ollama.

| Pieza | RAM estimada |
| --- | --- |
| Home Assistant OS (sistema y Supervisor) | 0,3 a 0,4 GB |
| Home Assistant Core con MQTT, Ollama, MCP y Assist | 0,5 a 0,9 GB (hay reportes de que crece) |
| PostgreSQL 18 + pgvector, con una base pequeña | 0,1 a 0,2 GB |
| Servidor: API, visión y MQTT | 0,15 a 0,25 GB (121 MB al arrancar, con YuNet y SFace) |
| MCP | Unos 0,1 GB (92 MB) |
| Mosquitto, y Samba mientras se copian archivos | Menos de 0,1 GB |
| **Todo, sin Ollama** | **1,2 a 1,9 GB** |
| `qwen2.5:0.5b` | Unos 0,7 GB |
| `qwen2.5:1.5b` (Q4_K_M) | Unos 1,85 GB |
| `qwen2.5:3b` (Q4_K_M) | Unos 3,0 GB |

- Con 4 GB cabe `qwen2.5:1.5b`, justo; el 3b no cabe sin usar swap. Con 8 GB cabe `qwen2.5:3b` con margen.
- La RAM real de cada complemento se mira en la Pi, en la página del complemento.

### Velocidad del agente en la Pi

- Cifras publicadas de llama.cpp en una Pi 5, en Q4_K_M: `qwen2.5:1.5b` procesa el prompt a unos 22 tokens/s y genera unos 9,6; `qwen2.5:3b`, unos 10,6 y 4,8. La variante Q4_0, reacomodada para ARM, procesó el prompt unas tres veces más rápido. Con Ollama hay que medirlo.
- Las instrucciones y las seis herramientas suman unos 1 000 tokens (medido abajo). Con esas cifras, procesarlas sin caché tardaría unos 45 s con 1.5b en Q4_K_M, y unos 15 s en Q4_0: más que los 15 s de RNF-03 · C3.
- **La caché del prompt.** Ollama reutiliza el comienzo del prompt que no cambió desde un pedido anterior. Home Assistant arma el prompt de sistema con nuestras instrucciones, el texto que agrega la API de las herramientas y una línea propia con la fecha y la hora, con segundos (`Current time is …`), salvo que alguna herramienta tenga un nombre que termine en `GetDateTime`. Las herramientas van después: en la plantilla de Qwen2.5 quedan detrás de ese texto.
  - Hasta `mcp-agente.md` 1.4, esa línea cambiaba en cada pregunta, y Ollama volvía a procesar las herramientas: unos 750 tokens por pregunta.
  - Desde la 1.5, `fecha_y_hora_GetDateTime` hace que Home Assistant no agregue la línea, y las instrucciones ya no llevan la hora. Desde la segunda pregunta, Ollama solo procesa la pregunta.
  - Dentro de una misma pregunta, la segunda llamada al modelo, la que lleva la respuesta de la herramienta, reutiliza todo.
- **Medido** el 2026-11-13 en el portátil, con `servidor/scripts/cache_del_prompt.py`: Ollama 0.40.16 solo con CPU, `qwen2.5:1.5b`, recién arrancado y con cada pregunta en una conversación nueva. En Ollama 0.40, `prompt_eval_count` cuenta todo el prompt y `prompt_eval_cached_count`, lo que salió de la caché:

| Escenario | Pregunta | Tokens del prompt | De la caché | Procesados | Tiempo |
| --- | --- | --- | --- | --- | --- |
| 1.4 | ¿Quién llegó tarde ayer? | 958 | 3 | 955 | 2 570 ms |
| 1.4 | ¿Qué hora es? | 955 | 206 | 749 | 2 170 ms |
| 1.4 | ¿Hubo desconocidos en las últimas 24 horas? | 965 | 205 | 760 | 2 137 ms |
| 1.5 | ¿Quién llegó tarde ayer? | 998 | 30 | 968 | 2 550 ms |
| 1.5 | ¿Qué hora es? | 995 | 986 | 9 | 168 ms |
| 1.5 | ¿Hubo desconocidos en las últimas 24 horas? | 1 005 | 986 | 19 | 103 ms |

  El modelo pidió `fecha_y_hora_GetDateTime` solo con «¿Qué hora es?». Los tiempos son de la CPU del portátil, no de la Pi.
- **En la Pi**, la primera pregunta después de arrancar Ollama todavía procesa todo el prompt: unos 45 s con 1.5b en Q4_K_M, con las cifras publicadas. Las siguientes procesan solo la pregunta. Los tiempos reales se miden en la C2.
- Si una respuesta pasa de 15 s, se sigue RNF-03 · C3.

### Cómo se prueban sin la Pi

1. **CI**, con `complementos.yml`: construye los dos complementos para arm64, con QEMU, y para amd64; en amd64 los arranca con un `options.json` de prueba y revisa `/api/v1/salud` y un `initialize` del MCP.
2. **Portátil:** `docker buildx build --platform linux/arm64` y `docker run --platform linux/arm64`, con `/data` montada. Es emulado y lento, pero comprueba que arranca.
3. **Ensayo completo:** el devcontainer oficial de Home Assistant, que corre Supervisor y Home Assistant en Docker en el portátil (`http://localhost:7123`). Ahí se instalan nuestros complementos locales, Mosquitto y Ollama, y se prueban los archivos de Home Assistant de la C2.
4. **En la Pi:** la RAM de cada complemento, las 10 preguntas con sus tiempos y que la puerta abra en menos de 2 s.

## Servicios de Docker Compose

Desde D-22, Compose es para desarrollar en el portátil y para el plan B; en la demo, las mismas piezas son los complementos de arriba. Archivo principal: `infra/compose.yaml`. Home Assistant va en la red de Docker, no en modo host (D-19).

| Servicio | Imagen | Puerto interno | Publicado en el equipo | Quién lo usa |
| --- | --- | --- | --- | --- |
| `postgres` | `pgvector/pgvector:pg18` | 5432 | `127.0.0.1:${POSTGRES_PORT}` (5434 por defecto) | `servidor`, `mcp`, pruebas |
| `mosquitto` | `eclipse-mosquitto:2` | 1883 | `1883` en la red | `servidor`, placa, simulador, Home Assistant |
| `servidor` | `accesia-servidor` (propia, `servidor/Dockerfile` con la raíz del repositorio como contexto) | 8000 | `8000` en la red | cámara, simulador, web |
| `mcp` | `accesia-servidor` (misma imagen, comando `accesia mcp`) | 8001 | no se publica | Home Assistant |
| `homeassistant` | `ghcr.io/home-assistant/home-assistant:stable` | 8123 | `8123` en la red | navegador |
| `ollama` | `ollama/ollama` | 11434 | no se publica | Home Assistant |

- Volúmenes: `datos-postgres`, `datos-ollama` y `datos-mosquitto`. `datos-postgres` se monta en `/var/lib/postgresql`: PostgreSQL 18 guarda los datos en `/var/lib/postgresql/18/docker`, no en `/var/lib/postgresql/data`. La configuración de Home Assistant se monta desde `homeassistant/config`.
- La imagen del servidor se construye con la raíz del repositorio como contexto, para copiar `specs/contratos/base-de-datos.sql` y el texto de `specs/consentimiento.md`, y para compilar la web (`web/`) sin el simulacro. El servidor sirve la web en la raíz del mismo puerto 8000 (D-04), y `/api` no cambia. Un `.dockerignore` en la raíz deja fuera `datos/`, `kit/`, `node_modules/` y lo que la web compila o genera en el PC, como `web/dist/`.
- El servidor corre con un solo proceso de Uvicorn: la hora de la última alerta de R6, el control del 429 y la conexión MQTT viven en memoria, y con varios procesos cada uno contaría por su lado.
- Las versiones exactas de las imágenes se fijan el Día 4, antes de armar el kit.
- Escenario 2 (Home Assistant OS, Mosquitto y Ollama en la Raspberry, y la base, el servidor y el MCP en el portátil), plan B desde D-22: `infra/compose.escenario2.yaml` publica `mcp` (8001) en la red del portátil, para que la Raspberry lo alcance; lo crea la C2 del Día 3. `infra/compose.broker-pi.yaml` conecta el servidor al Mosquitto de la Pi, en `IP_DE_LA_PI`, y no arranca el del Compose (D-23). Ollama sigue en la Pi, salvo el caso de abajo. Solo se usa en el hotspot del portátil o en otra red propia, y es una excepción a D-16 y D-19. Si la Pi no tiene Mosquitto, se usa sin `compose.broker-pi.yaml`, con el broker del portátil.
- Ollama en el portátil (RNF-03 · C3), solo con el visto bueno del profesor (D-22): `infra/compose.ollama-portatil.yaml` levanta solo `ollama` en el portátil y publica el 11434 en la red propia; Home Assistant sigue en la Raspberry. Lo crea la tarea del kit del Día 4. Es otra excepción a D-19.
- El servicio `mcp` no recibe `infra/.env`: Compose le arma `DATABASE_URL` con el usuario `agente` y `AGENTE_DB_PASSWORD`, y le pasa `ZONA_HORARIA` y `MCP_HOSTS_PERMITIDOS`. Así nunca tiene la clave del dueño de la base (D-15).

Direcciones dentro de la red de Docker: `http://servidor:8000`, `http://mcp:8001/mcp`, `http://ollama:11434`, `mqtt://mosquitto:1883`.

## Configuración (`infra/.env`)

`infra/.env` no se sube a Git. `infra/.env.example` lleva los mismos nombres sin claves. Compose arma con estas variables `DATABASE_URL` y `MQTT_URL` para el servidor, y la `DATABASE_URL` del usuario `agente` para `mcp`. En la Pi (D-22), estos valores van en las opciones de los complementos.

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
| `MQTT_HA_CLAVE` | (clave) | Usuario MQTT `homeassistant` en el broker del portátil. En la Pi, ese usuario lo maneja Home Assistant OS |
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
| `OLLAMA_MODELO` | `qwen2.5:3b` | Modelo que se descarga para el agente en Compose (D-06). En la Pi, el modelo depende de su RAM (D-22) |
| `MCP_HOSTS_PERMITIDOS` | `192.168.137.1:8001` | Encabezados `Host` que acepta el servidor MCP además de `mcp:8001`, separados por comas. En el escenario 2 (plan B de D-22), la IP del portátil en el hotspot. Si falta, Compose usa `192.168.137.1:8001`. En la Pi, el complemento la pone en `local-accesia-servidor:8001` |
| `IP_DE_LA_PI` | `192.168.137.250` | La IP de la Pi en el hotspot, solo para `compose.broker-pi.yaml` (plan B, D-23): el servidor del portátil usa el Mosquitto de esa IP. Si falta, Compose usa `192.168.137.250` |

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
| `servidor <url>` | `servidor http://192.168.137.250:8000` |
| `codigo <codigo>` | `codigo entrada` |
| `token <token>` | El token que da la web al crear la cámara |
| `mqtt <url> <usuario> <clave>` | `mqtt mqtt://192.168.137.250:1883 camara clave123` |
| `puerta <pin> <segundos> [bajo\|alto]` | `puerta 15 3 bajo`, lo de fábrica en el C6. El nivel es el que enciende; `-1` si no hay LED ni relé |
| `sensor <dht22\|dht11>` | `sensor dht11` |
| `antena <interna\|externa>` | `antena externa` |
| `reiniciar` | Reinicia la placa |
| `ayuda` | Lista los comandos |

Los valores de fábrica apuntan a la Pi (D-22): servidor `http://192.168.137.250:8000` y MQTT `mqtt://192.168.137.250:1883`, con el usuario `camara`. La IP está en un solo lugar, `ACCESIA_IP_DE_LA_PI` en `valores_de_fabrica.hpp`. Si en clase es otra (P-04), se cambia ahí y se recompila, o en la placa con `servidor` y `mqtt`, sin recompilar. Los comandos `perfil`, `pin` y `cara_min` son del firmware del ESP32-S3 y vuelven con él.

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

- Red de la demo: el hotspot de Windows del portátil, en 2,4 GHz, porque el C6 no usa 5 GHz (D-21). El portátil queda en una IP que no cambia, que suele ser `192.168.137.1`.
- La Pi tiene una IP fija en esa red, que se le pone en la configuración de red de Home Assistant OS: por ejemplo `192.168.137.250`, a confirmar en clase (D-22). La placa y el simulador apuntan a `http://<IP de la Pi>:8000` y a `mqtt://<IP de la Pi>:1883`.
- En la demo, los puertos que se usan son los de la Pi: el 8000 (API y web) y el 1883 (MQTT). El firewall del portátil solo cuenta en el plan B (escenario 2): ahí deja entrar desde `192.168.137.0/24` el 8001 (`mcp`), el 8000 cuando la placa envíe recortes, el 1883 solo si el broker vuelve al portátil (D-23) y el 11434 solo si Ollama va al portátil.
- Escenario 1 (plan C): la Raspberry crea el Wi-Fi «AccesIA» en 2,4 GHz (`band bg` en NetworkManager) y queda en `10.42.0.1`.
- Plan B de red: la red del salón o el hotspot de un celular; la placa se reconfigura por consola serial.

| Escenario | Qué trae la Raspberry | Dónde corre cada cosa | Papel |
| --- | --- | --- | --- |
| Demo (D-22) | Home Assistant OS | Todo en la Raspberry, como complementos de Home Assistant OS | La demo |
| 2 | Home Assistant OS | Home Assistant, Mosquitto y Ollama en la Raspberry; la base, el servidor y el MCP en un portátil con `compose.escenario2.yaml` y `compose.broker-pi.yaml` (D-23) | Plan B |
| 1 | Raspberry Pi OS | Todo en la Raspberry con `infra/compose.yaml` | Plan C |
| 3 | Nada | Raspberry Pi OS en una memoria USB y se sigue como en el escenario 1. Pi 5: arranca desde USB sin configurar nada; Pi 4: solo si su bootloader ya lo permite | Plan C |

Si la Raspberry tiene 2 GB o menos, no alcanza para todo: se usa el escenario 2, y Ollama solo va al portátil con el visto bueno del profesor. Los pasos completos están en `docs/guia-dia-de-clase.md`.
