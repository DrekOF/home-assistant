<!--
Nombre: README.md
Descripción: Índice de los contratos de AccesIA, cómo cambian y cómo se prueban.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Contratos

Son el acuerdo entre frentes: con ellos cada uno trabaja por su lado sin pisar a los demás. Mandan sobre el código.

| Contrato | Archivo | Versión | Dueño | Lo usan |
| --- | --- | --- | --- | --- |
| Cámara → servidor | [api-dispositivo.md](api-dispositivo.md) | 1.0 | B | A (firmware y simulador) |
| API REST | [openapi.yaml](openapi.yaml) | 1.0 | B | C (web), A (simulador) |
| MQTT y Home Assistant | [mqtt.md](mqtt.md) | 1.0 | B | A (cámara), C (Home Assistant) |
| Agente (MCP) | [mcp-agente.md](mcp-agente.md) | 1.0 | B | C (Home Assistant) |
| Base de datos | [base-de-datos.sql](base-de-datos.sql) | 1.0 | B | B (servidor y MCP) |

## Cómo cambia un contrato

1. Quien necesita el cambio lo propone en un PR que toca el contrato y explica por qué.
2. Lo aprueban los frentes que lo usan.
3. Sube la versión: 1.1 si solo agrega algo compatible (un campo opcional, una ruta nueva); 2.0 si rompe algo (cambia o quita un campo, un tema o un código).
4. Se anota en el registro de cambios de `../decisiones.md`; si rompe algo, también en la bitácora.
5. Después cambia el código, con sus pruebas de contrato al día.

## Pruebas de contrato

Cada contrato tiene pruebas con la marca `contrato <nombre> · <caso>`:

- Servidor: cada respuesta y error de `api-dispositivo.md`, cada tema MQTT, cada herramienta del agente, el esquema migrado igual a `base-de-datos.sql` y las respuestas de la API validadas contra `openapi.yaml`.
- Web: los tipos se generan desde `openapi.yaml`; si el contrato cambia y la web no, TypeScript no compila.
- Simulador: un modo que envía las fotos de `datos/prueba/` y compara las respuestas.

## Revisión al crear el kit (2026-11-11)

- `openapi.yaml` pasa `openapi-spec-validator` (OpenAPI 3.1).
- `base-de-datos.sql` se cargó en un PostgreSQL 16 de prueba, con `vector` y `uuidv7` simulados. Se comprobaron las restricciones, las vistas del agente, que el usuario `agente` solo puede leer esas vistas y el borrado en cascada.
- Falta cargarlo en PostgreSQL 18 con pgvector real: lo hace la tarea B del Día 1.
