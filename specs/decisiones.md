<!--
Nombre: decisiones.md
Descripción: Decisiones de AccesIA con su motivo, y registro de cambios.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.5
-->

# Decisiones

La decisión central es D-02: la cámara detecta y el servidor reconoce, porque no tendremos hardware hasta la clase y todo debe probarse antes con la webcam.

## Decisiones del plan

| Código | Decisión | Por qué |
| --- | --- | --- |
| D-01 | Un punto de acceso en la demo: una cámara ESP32-S3 que sirve para acceso y asistencia. El diseño admite más cámaras. | Es lo que se puede mostrar bien en una clase. |
| D-02 | El ESP32-S3 detecta la cara con TinyML (detección de ESP-DL, int8) y envía solo el recorte. El servidor saca la huella con OpenCV (YuNet + SFace) y la compara en PostgreSQL con pgvector. | Sin placa no se puede probar el firmware. Así el reconocimiento se prueba entero con la webcam, la huella no depende de la placa y hay plan B si el firmware falla. |
| D-03 | La puerta la abre una regla: similitud ≥ umbral, persona activa y con consentimiento. El agente nunca decide un acceso. | Una regla responde siempre igual y se puede probar. En la Raspberry el modelo tarda segundos. |
| D-04 | Firmware en C++ con ESP-IDF; servidor en Python 3.13 con FastAPI; PostgreSQL + pgvector; Mosquitto; Home Assistant en contenedor; Ollama; web en React + Vite servida por el servidor. Todo con Docker Compose, en arm64 y amd64. | Un solo lenguaje en el servidor, el agente y el simulador. React ya lo conocen. |
| D-05 | Home Assistant se integra por MQTT con descubrimiento automático: el servidor publica las entidades y HA abre la puerta con una automatización. | Es la integración estándar: las entidades aparecen solas. |
| D-06 | Agente: Ollama local y herramientas de solo lectura en un servidor MCP del backend, usado desde Assist con las integraciones de Ollama y de MCP. Modelo: qwen2.5:3b con 8 GB o más; qwen2.5:1.5b con 4 GB. Si en la medición del Día 3 no llega a 9 de 10 preguntas, se prueba un modelo más reciente de tamaño parecido y se actualiza esta decisión. | El agente queda integrado a Home Assistant sin construir otro chat. |
| D-07 | Privacidad (Ley 1581): consentimiento explícito y registrado antes de inscribir. Se informa que no es obligatorio y hay registro manual de la asistencia (RF-06 · C5). No se guardan fotos, solo huellas; se borran a pedido. | Los datos biométricos son datos sensibles. |
| D-08 | Red propia: la Raspberry crea el Wi-Fi «AccesIA» en 2,4 GHz (el ESP32-S3 no usa 5 GHz) con IP fija 10.42.0.1. Plan B: la red del salón o un hotspot, configurando el ESP32-S3 por consola serial. | No depender del portal ni de las restricciones de la red de la universidad. |
| D-09 | Kit listo antes de la clase en un portátil (copia en una memoria USB si hay): imágenes arm64, modelo de Ollama, configuración y copia de seguridad de HA, binarios del firmware por placa y scripts. No depende de tener una microSD propia. | En clase solo se flashea, se copia y se inscribe, con lo que traiga la Raspberry. |
| D-10 | Un simulador con la webcam del portátil cumple el mismo contrato del ESP32-S3: detecta, recorta y envía. | Permite desarrollar sin hardware y es el plan C de la demo. |
| D-11 | Método: specs, CLAUDE.md y Claude Code; una rama por tarea; pruebas primero en las reglas. La web usa seis skills de frontend (taste completo, impeccable, Emil Kowalski, frontend-design, refactoring-ui y web-design-guidelines) y se verifica con Playwright. | Es el método que ya funcionó en InspectIA, en versión corta. |

## Decisiones del kit (propuestas; se aceptan en la tarea 00 del Día 1)

| Código | Decisión | Por qué |
| --- | --- | --- |
| D-12 | El proyecto se llama AccesIA. Los temas MQTT empiezan por `accesia/` (reemplaza `acceso/` del plan). | Nombre elegido el 11/11/2026; el prefijo evita choques con otros temas del broker. |
| D-13 | La inscripción es una sesión propia (tabla `inscripcion`): la web la abre para una persona y una cámara, las siguientes caras válidas de esa cámara son sus muestras, vence a los 120 s y solo hay una activa por cámara (R9). Reemplaza «modo y persona en inscripción» dentro de `dispositivo`. | Deja rastro de cada inscripción, permite ver el avance y cancelar, y la cámara no cambia. |
| D-14 | Los valores de las reglas van en `infra/.env` y se cambian reiniciando el servidor, sin recompilar. | En clase se recalibra el umbral en un minuto. |
| D-15 | El agente es de solo lectura en tres capas: sus herramientas no escriben; el usuario de base `agente` solo puede consultar vistas sin documento ni huellas; cada consulta corre en una transacción de solo lectura. En Home Assistant, el agente solo tiene las herramientas de AccesIA: «Control de dispositivos» queda apagado y el botón de la puerta no se expone a Assist. | Si una capa falla, las otras impiden que el agente cambie datos o abra la puerta. |
| D-16 | El servidor MCP no se publica fuera de la red de Docker y no pide clave. Excepción: en el escenario 2 se publica en la red del portátil (`compose.escenario2.yaml`), solo en la red propia o en un hotspot. | La integración MCP de Home Assistant solo admite OAuth. Dentro de la red de Docker y con solo lectura, el riesgo es aceptable para la demo; queda documentado. |
| D-17 | El firmware se compila en dos binarios, uno por tipo de PSRAM, que se fija al compilar: `octal` (perfiles `esp32s3_eye`, `freenove_s3_cam`, `xiao_s3_sense` y `generico_octal`, que se eligen con el comando `perfil`) y `quad` (`generico_quad`). En los perfiles genéricos los pines se ajustan por consola serial. Corrige el plan, que decía que la PSRAM también se ajustaba por consola, y la versión 1.0 de `arquitectura.md`, que tenía un binario por perfil. | ESP-IDF elige el modo de la PSRAM en la configuración de compilación. |
| D-18 | La cámara envía los recortes por HTTP y usa MQTT solo para la puerta, su estado y su disponibilidad. El servidor publica los eventos y el descubrimiento. | HTTP da la respuesta al instante a la cámara; MQTT es lo que Home Assistant entiende. |
| D-19 | Home Assistant corre en la red de Docker, no en modo host: llega a `mosquitto`, `ollama` y `mcp` por su nombre. Excepciones: el escenario 2 publica `mcp` y `ollama` en la red del portátil, y si Ollama va al portátil (RNF-03 · C3), `infra/compose.ollama-portatil.yaml` lo publica en la red propia. | Funciona igual en Windows con Docker Desktop y en la Raspberry, y no expone Ollama ni el MCP. |

## Decisiones del equipo durante el proyecto

| Código | Decisión | Por qué |
| --- | --- | --- |
| D-20 | Horarios por bloques: cada horario tiene un nombre y bloques de día, hora de inicio y tolerancia en minutos, con un bloque por día como máximo porque la llegada es una por día. Una persona sigue teniendo un horario o ninguno. R5 usa el bloque del día de la llegada; si ese día no hay bloque, la llegada es `sin_horario`. | Una misma clase puede empezar a horas distintas según el día (por ejemplo, el lunes a las 07:00 y el miércoles a las 18:00), y con una sola hora por horario no se podía representar. |

## Registro de cambios

| Fecha | Decisión | Cambio |
| --- | --- | --- |
| 2026-11-11 | D-01 a D-11 | Tomadas del plan del proyecto. |
| 2026-11-11 | D-12 a D-19 | Propuestas al armar el kit del repositorio. |
| 2026-11-11 | Contratos 1.1 | Los cinco contratos pasan a la versión 1.1 con los acuerdos de la tarea 00 sobre la revisión `docs/revisiones/2026-11-11-revision-contratos-v1.md`; entre paréntesis va el punto de la revisión. Se agrega `contratos/casos-recorte.json`. |
| 2026-11-11 | D-11 | Repositorio privado sin proteger `main`, porque GitHub Free no lo permite: el PR con pruebas en verde queda por disciplina (2.1). CI desde el Día 1 en dos workflows, `servidor.yml` (tarea B) y `web.yml` (tarea C); el firmware se suma el Día 4 (2.2). Los skills de frontend quedan en commits fijos, con una opción para actualizarlos a propósito (3.10). |
| 2026-11-11 | D-07 · RF-06 | Registro manual de asistencia: `POST /api/v1/asistencia` con R5 aplicado a la hora dada y 409 `asistencia_duplicada`; columnas `asistencia.origen` y `asistencia.registrado_por`; asistencia de una persona en `GET /api/v1/personas/{persona_id}/asistencia` (RF-12 · C3). La API va el Día 3 de B y el botón el Día 3 de C (1.3). |
| 2026-11-11 | R4 · D-05 | Un `permitido` repetido publica el evento con `repetido: true` para que Home Assistant abra la puerta; no guarda otro evento ni cambia la asistencia. Un `denegado` repetido no publica nada (1.7). |
| 2026-11-11 | D-17 | Dos binarios por tipo de PSRAM: `octal` (`esp32s3_eye`, `freenove_s3_cam`, `xiao_s3_sense` y `generico_octal`, elegibles con `perfil`) y `quad` (`generico_quad`) (1.8). El diagnóstico se compila con `CONFIG_SPIRAM_IGNORE_NOTFOUND=y` (3.1). |
| 2026-11-11 | R7 | El paso 5 busca solo entre las muestras de otras personas (1.9). Paso 6 nuevo: desde la segunda muestra, cada una se parece a la primera aceptada de la inscripción; si no, `distinta_de_la_primera` (3.7). El servidor descarta por tamaño solo si la cara mide menos de 0,8 × `CARA_MIN_PX`, al reconocer y al inscribir (3.3). |
| 2026-11-11 | R3 · R6 · R9 | R3: `sin_consentimiento` queda como defensa y se agrega el caso de punta a punta (1.2). R6: cuentan los desconocidos de hace menos de la ventana, como en R4 (1.12). R9: la inscripción también vence al abrir otra en la cámara y al listar las cámaras (1.5); revocar el consentimiento cancela la inscripción activa, desactivar a la persona no (1.6). |
| 2026-11-11 | Contrato cámara | Fórmula del recorte con dos ejemplos (2.3). La cámara espera 1 s desde cada respuesta y el servidor responde 429 solo si llegan dos recortes en menos de 0,8 s (3.4). En la inscripción, `persona` es siempre quien se inscribe (1.10). |
| 2026-11-11 | Contrato MQTT | El código `servidor` queda reservado y la ACL de `camara` usa `pattern` con el client id (1.1). `EstadoCamara.firmware` usa el mismo texto que la cabecera `X-AccesIA-Firmware` (1.12). Las automatizaciones van en `automatizaciones_accesia.yaml`, incluido desde `configuration.yaml` (3.11). El resumen también se publica después de una llegada manual (1.3). |
| 2026-11-11 | Contrato API | `GET /api/v1/personas/{persona_id}/consentimiento` responde `null` sin consentimiento vigente; historial en `GET /api/v1/personas/{persona_id}/consentimientos`; `aceptado_en` para el consentimiento en papel (1.12). El código `servidor` se rechaza al crear una cámara (1.1). |
| 2026-11-11 | Contrato agente | Formato de las horas que mezclan días, valores por defecto de `llegadas_tarde`, encabezado `Host` del MCP (1.12 y 3.11) y primera medición del Día 3 (3.6). |
| 2026-11-11 | D-06 | El agente se mide primero el Día 3 en el portátil; si no llega a 9 de 10, se prueba un modelo más reciente de tamaño parecido (3.6). |
| 2026-11-11 | D-08 | El Wi-Fi propio va en 2,4 GHz (3.11). |
| 2026-11-11 | D-16 · D-19 | Se escriben las excepciones: el escenario 2 y `infra/compose.ollama-portatil.yaml` (Día 4 de C) publican servicios en la red propia (1.11). |
| 2026-11-11 | Plan | Día 2 de B: sesión, primer administrador, personas, consentimiento, horarios, cámaras y comando `crear-camara`; Día 2 de C: también la pantalla Cámaras; `semilla agente` el Día 3 de B (2.7). |
| 2026-11-11 | Arquitectura y tareas | Imagen del servidor con la raíz del repositorio como contexto (2.4); un solo proceso de Uvicorn (3.5); modo «como la cámara» del simulador y recalibración en clase (3.2); versión de ESP-DL compatible con ESP-IDF 5.4 (2.6); pruebas del firmware con CMake y doctest en WSL (2.5); volumen de PostgreSQL 18, `listener 1883`, `ADMIN_CORREO` y `tzdata` (3.9); puertos reservados de Windows y `.ps1` con BOM (3.8). |
| 2026-11-11 | Texto del consentimiento | «Qué datos» nombra el registro de entradas. Sigue siendo la versión 1.0 del texto porque nadie la había aceptado (1.4). |
| 2026-11-11 | Repositorio | `.gitignore` ignora `firmware/build-*/` y ya no ignora `dependencies.lock`; la rama de cambios de contratos usa el prefijo `b/` (1.12). |
| 2026-11-11 | D-20 | Horarios por bloques: tabla `horario_bloque`, R5 con el bloque del día de la llegada, requisito RF-13 y pantalla Horarios en el Día 3 de C. |
| 2026-11-11 | Contratos 1.2 | `base-de-datos.sql`, `openapi.yaml` y `mcp-agente.md` pasan a 1.2 por D-20. El esquema `Horario` cambia de campos, así que rompe la 1.1; según `contratos/README.md` eso sería 2.0, pero se dejó en 1.2 porque todavía no hay código que lo use. |
| 2026-11-11 | D-11 | Los skills de frontend pasan a seis: se suman refactoring-ui (`wondelai/skills`) y web-design-guidelines (`vercel-labs/agent-skills`), con commit fijo como los demás. |
| 2026-11-12 | Plan | Tareas del Día 2 en `tareas/dia-2/`. La tarea B se divide en B1 (sesión, personas, consentimiento, horarios, cámaras, `crear-camara` y el contrato de la API 1.3) y B2 (reconocimiento, R1 a R4, R7 e inscripción), para que cada PR se pueda revisar. B1 propone en su PR el contrato de la API 1.3: el código de error `metodo_no_permitido` para el 405, que hoy responde `no_encontrado`, y el campo `Dispositivo.inscripcion_activa`, para encontrar la inscripción activa de una cámara si se pierde su id. |
| 2026-11-12 | Contrato API 1.3 | `openapi.yaml` suma el código de error `metodo_no_permitido`, para el 405 que antes respondía `no_encontrado`, y el campo `Dispositivo.inscripcion_activa` (`InscripcionCorta` o `null`), para que la web encuentre la inscripción activa de una cámara si pierde su id. Los dos solo agregan. Tarea B1 del Día 2. |
