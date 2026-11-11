<!--
Nombre: decisiones.md
Descripción: Decisiones de AccesIA con su motivo, y registro de cambios.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
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
| D-06 | Agente: Ollama local y herramientas de solo lectura en un servidor MCP del backend, usado desde Assist con las integraciones de Ollama y de MCP. Modelo: qwen2.5:3b con 8 GB o más; qwen2.5:1.5b con 4 GB. | El agente queda integrado a Home Assistant sin construir otro chat. |
| D-07 | Privacidad (Ley 1581): consentimiento explícito y registrado antes de inscribir. Se informa que no es obligatorio y hay registro manual. No se guardan fotos, solo huellas; se borran a pedido. | Los datos biométricos son datos sensibles. |
| D-08 | Red propia: la Raspberry crea el Wi-Fi «AccesIA» con IP fija 10.42.0.1. Plan B: la red del salón o un hotspot, configurando el ESP32-S3 por consola serial. | No depender del portal ni de las restricciones de la red de la universidad. |
| D-09 | Kit listo antes de la clase en un portátil (copia en una memoria USB si hay): imágenes arm64, modelo de Ollama, configuración y copia de seguridad de HA, binarios del firmware por placa y scripts. No depende de tener una microSD propia. | En clase solo se flashea, se copia y se inscribe, con lo que traiga la Raspberry. |
| D-10 | Un simulador con la webcam del portátil cumple el mismo contrato del ESP32-S3: detecta, recorta y envía. | Permite desarrollar sin hardware y es el plan C de la demo. |
| D-11 | Método: specs, CLAUDE.md y Claude Code; una rama por tarea; pruebas primero en las reglas. La web usa los skills de frontend (taste completo, impeccable, Emil Kowalski y frontend-design) y se verifica con Playwright. | Es el método que ya funcionó en InspectIA, en versión corta. |

## Decisiones del kit (propuestas; se aceptan en la tarea 00 del Día 1)

| Código | Decisión | Por qué |
| --- | --- | --- |
| D-12 | El proyecto se llama AccesIA. Los temas MQTT empiezan por `accesia/` (reemplaza `acceso/` del plan). | Nombre elegido el 11/11/2026; el prefijo evita choques con otros temas del broker. |
| D-13 | La inscripción es una sesión propia (tabla `inscripcion`): la web la abre para una persona y una cámara, las siguientes caras válidas de esa cámara son sus muestras, vence a los 120 s y solo hay una activa por cámara (R9). Reemplaza «modo y persona en inscripción» dentro de `dispositivo`. | Deja rastro de cada inscripción, permite ver el avance y cancelar, y la cámara no cambia. |
| D-14 | Los valores de las reglas van en `infra/.env` y se cambian reiniciando el servidor, sin recompilar. | En clase se recalibra el umbral en un minuto. |
| D-15 | El agente es de solo lectura en tres capas: sus herramientas no escriben; el usuario de base `agente` solo puede consultar vistas sin documento ni huellas; cada consulta corre en una transacción de solo lectura. En Home Assistant, el agente solo tiene las herramientas de AccesIA: «Control de dispositivos» queda apagado y el botón de la puerta no se expone a Assist. | Si una capa falla, las otras impiden que el agente cambie datos o abra la puerta. |
| D-16 | El servidor MCP no se publica fuera de la red de Docker y no pide clave. | La integración MCP de Home Assistant solo admite OAuth. Dentro de la red de Docker y con solo lectura, el riesgo es aceptable para la demo; queda documentado. |
| D-17 | En el perfil genérico de placa los pines se ajustan por consola serial, pero el tipo de PSRAM (octal o quad) se fija al compilar: hay dos binarios genéricos. Corrige el plan, que decía que la PSRAM también se ajustaba por consola. | ESP-IDF elige el modo de la PSRAM en la configuración de compilación. |
| D-18 | La cámara envía los recortes por HTTP y usa MQTT solo para la puerta, su estado y su disponibilidad. El servidor publica los eventos y el descubrimiento. | HTTP da la respuesta al instante a la cámara; MQTT es lo que Home Assistant entiende. |
| D-19 | Home Assistant corre en la red de Docker, no en modo host: llega a `mosquitto`, `ollama` y `mcp` por su nombre. | Funciona igual en Windows con Docker Desktop y en la Raspberry, y no expone Ollama ni el MCP. |

## Registro de cambios

| Fecha | Decisión | Cambio |
| --- | --- | --- |
| 2026-11-11 | D-01 a D-11 | Tomadas del plan del proyecto. |
| 2026-11-11 | D-12 a D-19 | Propuestas al armar el kit del repositorio. |
