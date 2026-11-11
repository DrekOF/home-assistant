<!--
Nombre: plan.md
Descripción: Plan de AccesIA por días, frentes e hitos, con el corte mínimo.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Plan

Tres frentes en paralelo durante cinco días de trabajo, con tres hitos que comprueban que todo encaja. El Día 5 es el ensayo general y después viene la clase. Si la clase llega antes, se aplica el corte mínimo y se adelanta el ensayo.

Si un hito no se cumple, se resuelve antes de seguir. Cada frente usa el simulador, así que nadie depende del hardware.

## Frentes

| Frente | Responsable | Entrega |
| --- | --- | --- |
| A · Cámara y TinyML | Julián Andrés Silva Morales | Firmware del ESP32-S3 por placa, firmware de diagnóstico y de respaldo, simulador y calibración del umbral |
| B · Servidor, datos y agente | Cristhian Eduardo Sánchez Mosquera | API, reconocimiento, reglas, base de datos, MQTT y servidor MCP |
| C · Web, Home Assistant y despliegue | Jhon Jairo Perdomo Perdomo | Web, configuración de Home Assistant, imágenes arm64, kit del día de clase y pruebas de la web |

## Días

| Día | Frente | Tarea | Archivo |
| --- | --- | --- | --- |
| 1 | Todos | Acordar los contratos y crear el repositorio | `tareas/dia-1/00-todos-acordar-contratos.md` |
| 1 | A | Instalar ESP-IDF y compilar el firmware base con la detección de ESP-DL | `tareas/dia-1/A-julian-esp-idf-y-deteccion.md` |
| 1 | B | Docker Compose base, esquema de la base con migraciones y esqueleto del servidor | `tareas/dia-1/B-cristhian-compose-y-base.md` |
| 1 | C | Skills de frontend y web con inicio de sesión y Personas | `tareas/dia-1/C-jhon-skills-y-web.md` |
| 2 | A | Simulador con la webcam: detecta con YuNet, recorta y envía como el ESP32-S3 | se escribe al cerrar el Día 1 |
| 2 | B | Reconocimiento (YuNet + SFace + pgvector), reglas R1 a R4 y R7, e inscripción (R9) | se escribe al cerrar el Día 1 |
| 2 | C | Pantallas Personas (con consentimiento) e Inscripción conectadas a la API | se escribe al cerrar el Día 1 |
| 2 | Todos | **Hito 1:** el simulador inscribe y reconoce a alguien de punta a punta | — |
| 3 | A | Firmware: cámara, detección, recorte JPEG, envío por HTTP y puerta por MQTT | — |
| 3 | B | Asistencia (R5), alertas (R6), eventos y descubrimiento por MQTT, y servidor MCP | — |
| 3 | C | Home Assistant: MQTT, panel, automatizaciones y Assist con Ollama y MCP; pantallas Accesos y Asistencia | — |
| 3 | Todos | **Hito 2:** con el simulador, Home Assistant abre la puerta y Assist dice quién llegó tarde | — |
| 4 | A | Perfiles de placa, firmware de diagnóstico y de respaldo, compilación en GitHub Actions y calibración del umbral | — |
| 4 | B | Modo extraer, pruebas de las reglas completas y evaluación del agente con 10 preguntas | — |
| 4 | C | Imágenes arm64 probadas con emulación, kit en el portátil, scripts `instalar.sh` y `verificar.sh`, y Playwright sobre toda la web | — |
| 5 | Todos | Ensayo general del día de clase desde cero, con el kit y cronómetro | — |
| 5 | Todos | **Hito 3:** kit probado y guion de la sustentación listo | — |

## Alcance

Obligatorio para la demo:

1. Inscripción con consentimiento y 5 muestras desde la cámara.
2. Reconocimiento y acceso: recorte, huella, comparación, regla, evento y puerta.
3. Asistencia: llegada a tiempo o tarde y reporte del día.
4. Home Assistant: entidades por MQTT, panel y automatizaciones (puerta y desconocidos).
5. Agente: Ollama con las herramientas de solo lectura, usado desde Assist.
6. Firmware TinyML que detecta y envía, más el simulador.
7. Kit del día de clase y un ensayo general.

Extras, si sobra tiempo: resumen diario del agente como notificación, exportar la asistencia a CSV y registrar la salida, foto del desconocido en Home Assistant sin guardarla, chat del agente en la web y varias cámaras.

## Corte mínimo (si solo hay 2 o 3 días)

- Web con tres pantallas: Personas, Inscripción y Asistencia.
- Un solo perfil de placa más el firmware de respaldo.
- Agente con 3 herramientas: `asistencia_del_dia`, `llegadas_tarde` y `buscar_persona`.
- El ensayo general no se recorta.
