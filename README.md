<!--
Nombre: README.md
Descripción: Presentación de AccesIA y pasos para arrancar el Día 1.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# AccesIA

Control de acceso y asistencia con reconocimiento facial. Proyecto de la materia de Inteligencia Artificial, Universidad Surcolombiana.

**La cámara ve, el servidor reconoce, Home Assistant actúa y el agente responde.**

1. Ana se para frente a la cámara. El ESP32-S3 detecta su cara con un modelo TinyML y envía solo el recorte.
2. El servidor saca la huella de la cara (128 números) y busca la más parecida en PostgreSQL.
3. Si se parece lo suficiente y Ana está activa y dio su consentimiento, el acceso queda permitido y se anota su llegada (a tiempo o tarde).
4. Home Assistant recibe el resultado por MQTT, abre la puerta y muestra «Ana entró a las 7:58». Si nadie se parece, avisa.
5. En Assist, el chat de Home Assistant, el agente responde preguntas como «¿quién llegó tarde hoy?» usando Ollama, sin poder cambiar nada.

## Equipo

| Frente | Responsable | Qué construye |
| --- | --- | --- |
| A · Cámara y TinyML | Julián Andrés Silva Morales | Firmware del ESP32-S3, simulador y calibración del umbral |
| B · Servidor, datos y agente | Cristhian Eduardo Sánchez Mosquera | API, reconocimiento, reglas, base de datos, MQTT y servidor MCP |
| C · Web, Home Assistant y despliegue | Jhon Jairo Perdomo Perdomo | Web, configuración de Home Assistant, imágenes arm64 y kit de la clase |

## Cómo arrancar el Día 1

1. Abre esta carpeta en VS Code.
2. Inicia Git y haz el primer commit desde la terminal de VS Code:

   ```powershell
   git init -b main
   git add .
   git commit -m "Kit base del repositorio"
   ```

3. Crea el repositorio privado en GitHub, súbelo e invita a Julián y a Jhon.
4. Los tres leen juntos `tareas/dia-1/00-todos-acordar-contratos.md` (unos 45 minutos).
5. Cada uno abre su tarea del Día 1 en `tareas/dia-1/` y la trabaja con Claude Code, siguiendo `CLAUDE.md`.
6. Cuando la tarea de Jhon llegue a `main`, cada integrante trae los skills de frontend con `.\scripts\preparar-skills.ps1`.

## Dónde está cada cosa

| Carpeta | Qué tiene |
| --- | --- |
| `specs/` | Decisiones, arquitectura, requisitos, reglas, datos y plan. Empieza por `specs/README.md` |
| `specs/contratos/` | API, MQTT, herramientas del agente y base de datos |
| `tareas/` | Tareas para Claude Code, por día y por frente |
| `docs/` | Bitácora, guía del día de clase y diagramas |
| `firmware/`, `simulador/`, `servidor/`, `web/`, `homeassistant/`, `infra/` | El código, cada uno con su README |

## Documentos del plan

- Plan detallado: https://claude.ai/artifact/3WcKn79rx6c3Z2GDjZFdhf
- Tablero del plan (whiteboard): https://claude.ai/artifact/2iUjPM3Ug3y2dLm4RL7WT8
- Diagramas: `docs/diagramas/arquitectura-explicada.html` y `docs/diagramas/paso-a-paso.html` (se abren en el navegador)
