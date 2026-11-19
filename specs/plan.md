<!--
Nombre: plan.md
Descripción: Plan de AccesIA por días, frentes e hitos, con el corte mínimo.
Fecha de creación: 2026-11-11
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.8
-->

# Plan

Tres frentes en paralelo durante cinco días de trabajo, con tres hitos que comprueban que todo encaja. El Día 5 es el ensayo general y después viene la clase. Si la clase llega antes, se aplica el corte mínimo y se adelanta el ensayo.

Si un hito no se cumple, se resuelve antes de seguir. Cada frente usa el simulador, así que nadie depende del hardware.

## Frentes

| Frente | Responsable | Entrega |
| --- | --- | --- |
| A · Cámara y TinyML | Julián Andrés Silva Morales | Firmware de la XIAO ESP32-C6 (puerta, estado y sensor de ambiente; la cámara cuando llegue el módulo, D-21), simulador y calibración del umbral. El firmware del ESP32-S3 queda como referencia (PR #7) |
| B · Servidor, datos y agente | Cristhian Eduardo Sánchez Mosquera | API, reconocimiento, reglas, base de datos, MQTT, servidor MCP y los complementos de Home Assistant OS de la base y del servidor (D-22) |
| C · Web, Home Assistant y despliegue | Jhon Jairo Perdomo Perdomo | Web, configuración de Home Assistant, imágenes arm64, kit del día de clase y pruebas de la web |

## Días

| Día | Frente | Tarea | Archivo |
| --- | --- | --- | --- |
| 1 | Todos | Acordar los contratos y crear el repositorio | `tareas/dia-1/00-todos-acordar-contratos.md` |
| 1 | A | Instalar ESP-IDF y compilar el firmware base con la detección de ESP-DL | `tareas/dia-1/A-julian-esp-idf-y-deteccion.md` |
| 1 | B | Docker Compose base, esquema de la base con migraciones, esqueleto del servidor y CI del servidor (`servidor.yml`) | `tareas/dia-1/B-cristhian-compose-y-base.md` |
| 1 | C | Skills de frontend con commits fijos, web con inicio de sesión y Personas, y CI de la web (`web.yml`) | `tareas/dia-1/C-jhon-skills-y-web.md` |
| 2 | Todos | Orden entre las tareas del día y guion del Hito 1 | `tareas/dia-2/00-todos-orden-e-hito-1.md` |
| 2 | A | Simulador con la webcam y con una carpeta de fotos: detecta con YuNet, recorta y envía como el ESP32-S3, con el modo «como la cámara» | `tareas/dia-2/A-julian-simulador.md` |
| 2 | A | Specs del hardware real: D-21 y `mqtt.md` 1.2 (rama `b/hardware-c6`) | — |
| 2 | A | Firmware de la XIAO ESP32-C6: Wi-Fi, MQTT, puerta en el LED, sensor DHT con su descubrimiento y `firmware.yml` (rama `a/firmware-c6`) | — |
| 2 | B1 | Sesión y primer administrador; API de personas, consentimiento, horarios por bloques (D-20) y cámaras, con el comando `crear-camara`; contrato de la API 1.3 con `metodo_no_permitido` e `inscripcion_activa` | `tareas/dia-2/B1-cristhian-sesion-y-api.md` |
| 2 | B2 | Reconocimiento (YuNet + SFace + pgvector), reglas R1 a R4 y R7, e inscripción (R9) | `tareas/dia-2/B2-cristhian-reconocimiento-e-inscripcion.md` |
| 2 | C | Personas (con consentimiento) contra la API real, y pantallas Inscripción y Cámaras | `tareas/dia-2/C-jhon-inscripcion-y-camaras.md` |
| 2 | Todos | **Hito 1:** el simulador inscribe y reconoce a alguien de punta a punta | `tareas/dia-2/00-todos-orden-e-hito-1.md` |
| 3 | Todos | El Hito 1 primero; dependencias y orden entre las tareas del día, reparto entre tres sesiones, Docker Compose desde la carpeta principal y guion del Hito 2 | `tareas/dia-3/00-todos-orden-e-hito-2.md` |
| 3 | A1 | Puerta del simulador por MQTT, sin chocar con la placa que usa el mismo código | `tareas/dia-3/A1-julian-puerta-del-simulador.md` |
| 3 | A2 | Cámara de la placa cuando llegue el módulo: captura, TinyML y envío, según `arquitectura.md` (D-21). Si no llega, pasa al Día 4 | `tareas/dia-3/A2-julian-camara-de-la-placa.md` |
| 3 | B1 | Asistencia (R5) desde la cámara y su registro manual; API de accesos, reporte del día, asistencia de una persona, huellas (RF-12 · C1) y configuración | `tareas/dia-3/B1-cristhian-asistencia-y-consultas.md` |
| 3 | B2 | MQTT: disponibilidad, descubrimiento (con el `model` de D-21 y su limpieza), eventos (con la repetición de R4), alertas (R6), resumen y estado de las cámaras | `tareas/dia-3/B2-cristhian-mqtt.md` |
| 3 | B3 | Servidor MCP con las cinco herramientas, servicio `mcp` y comando `semilla agente` | `tareas/dia-3/B3-cristhian-mcp-y-semilla.md` |
| 3 | B | Specs de D-22, todo en la Raspberry Pi: la decisión, la arquitectura, los requisitos, `mqtt.md` 1.4, `mcp-agente.md` 1.4 y la C2 ajustada (rama `b/d-22-todo-en-la-pi`) | — |
| 3 | C1 | Pantallas Accesos, Asistencia (con el botón de registro manual) y Horarios (RF-13), y los datos de la persona en su ficha (RF-12) | `tareas/dia-3/C1-jhon-accesos-asistencia-y-horarios.md` |
| 3 | C2 | Home Assistant OS con todo en la Pi (D-22): Mosquitto oficial con la ACL, el complemento de Ollama y su modelo, MQTT, panel, automatizaciones y Assist con Ollama y el MCP del complemento del servidor (con la B4 del Día 4); ensayo en el devcontainer; `compose.escenario2.yaml` como plan B; copia de seguridad de Home Assistant OS; primera medición de las 10 preguntas del agente | `tareas/dia-3/C2-jhon-home-assistant-y-agente.md` |
| 3 | Todos | **Hito 2:** con el simulador, Home Assistant abre la puerta y Assist dice quién llegó tarde | `tareas/dia-3/00-todos-orden-e-hito-2.md` |
| 4 | Todos | Con D-22: lo que sigue del Día 3 (Hito 1, C1, C2 y A2); el Hito 2 en clase con la B4 y la C2 del Día 3 (si no alcanzan, MQTT y Home Assistant con el escenario 2 y el agente después de la B4); lo que necesita la placa o la Pi, que pasa al día de clase si el hardware solo está allá; dependencias y reparto entre tres sesiones, acuerdos y lo que debe quedar listo para el ensayo del Día 5 | `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md` |
| 4 | A1 | Calibración de `UMBRAL_SIMILITUD` y `NITIDEZ_MIN` (RNF-07) con quienes participen (los tres integrantes y quien más quiera, cada uno con su consentimiento) y un dataset público de impostores con licencia para este uso, que se borra al terminar, sin ensuciar la base | `tareas/dia-4/A1-julian-calibracion-del-umbral.md` |
| 4 | A2 | La placa con Home Assistant OS y el broker de la Pi, o el escenario 2 (RF-14 · C2 a C6), la lista «Por verificar» del firmware, el tiempo de la puerta y el binario para el kit. `firmware.yml` ya se adelantó el Día 2 (D-21); el diagnóstico y el respaldo del S3 quedan para cuando vuelva | `tareas/dia-4/A2-julian-placa-con-home-assistant.md` |
| 4 | A3 | Los valores de fábrica del firmware y los ejemplos del simulador, del portátil a la IP fija de la Pi (D-22) | `tareas/dia-4/A3-julian-ip-de-la-pi.md` |
| 4 | B1 | La web compilada dentro de la imagen y servida por el servidor (D-04), para que el kit y el ensayo no necesiten Node | `tareas/dia-4/B1-cristhian-web-en-el-servidor.md` |
| 4 | B2 | Modo extraer para las cámaras de respaldo (RF-10 · C4) | `tareas/dia-4/B2-cristhian-modo-extraer.md` |
| 4 | B3 | Evaluación final del agente con 10 preguntas en la Pi, con el modelo fijado según su RAM (RF-08 · C3; D-22), y una prueba de cobertura de las reglas y los requisitos (RNF-06 · C1), que reemplaza «pruebas de las reglas completas»: los 64 casos de las reglas ya tienen su prueba | `tareas/dia-4/B3-cristhian-evaluacion-del-agente-y-cobertura.md` |
| 4 | B4 | Complementos de Home Assistant OS de la base y del servidor (D-22): las dos carpetas, `scripts/empaquetar-complementos.ps1`, `complementos.yml` para arm64 y amd64, y la ACL de `mqtt.md` 1.4 con su prueba | `tareas/dia-4/B4-cristhian-complementos-de-la-base-y-del-servidor.md` |
| 4 | C1 | Kit del día de clase con D-22 (RF-11): las carpetas de los complementos, el modelo de Ollama, la copia cifrada de Home Assistant OS sin inscripciones, el binario del C6, las imágenes de los planes B y C con versiones fijas, `instalar` y `verificar` (en PowerShell y en `.sh`; `verificar` revisa la Pi desde el portátil) y la guía. `compose.ollama-portatil.yaml`, solo con el visto bueno del profesor | `tareas/dia-4/C1-jhon-kit-del-dia-de-clase.md` |
| 4 | C2 | Playwright sobre toda la web en la CI (RF-09 · C3) e imágenes arm64 del plan C probadas con emulación (RNF-04 · C1); los complementos los prueba B4 en arm64 (D-22) | `tareas/dia-4/C2-jhon-playwright-y-arm64.md` |
| 5 | Todos | Ensayo general del día de clase desde cero, con el kit y cronómetro | — |
| 5 | Todos | **Hito 3:** kit probado y guion de la sustentación listo | — |

## Alcance

Obligatorio para la demo:

1. Inscripción con consentimiento y 5 muestras desde la cámara.
2. Reconocimiento y acceso: recorte, huella, comparación, regla, evento y puerta.
3. Asistencia: llegada a tiempo o tarde y reporte del día.
4. Home Assistant: entidades por MQTT, panel y automatizaciones (puerta y desconocidos).
5. Agente: Ollama con las herramientas de solo lectura, usado desde Assist.
6. Firmware de la placa (puerta, estado y sensor de ambiente) y el simulador. La detección TinyML en la placa, cuando llegue el módulo de cámara (D-21).
7. Kit del día de clase y un ensayo general.

Extras, si sobra tiempo: resumen diario del agente como notificación, exportar la asistencia a CSV y registrar la salida, foto del desconocido en Home Assistant sin guardarla, chat del agente en la web, varias cámaras y una página de presentación con scroll storytelling para la sustentación, que cuente el recorrido: Ana llega, la cámara la detecta, el servidor la reconoce, Home Assistant abre la puerta y el agente responde.

## Corte mínimo (si solo hay 2 o 3 días)

- Web con tres pantallas: Personas, Inscripción y Asistencia. Las cámaras se crean con el comando `crear-camara`.
- El firmware de la XIAO ESP32-C6 con la puerta y el sensor; la cámara puede quedar en el simulador (D-21).
- Agente con 3 herramientas: `asistencia_del_dia`, `llegadas_tarde` y `buscar_persona`.
- El ensayo general no se recorta.
