<!--
Nombre: README.md
Descripción: Índice de los contratos de AccesIA, cómo cambian y cómo se prueban.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.6
-->

# Contratos

Son el acuerdo entre frentes: con ellos cada uno trabaja por su lado sin pisar a los demás. Mandan sobre el código.

| Contrato | Archivo | Versión | Dueño | Lo usan |
| --- | --- | --- | --- | --- |
| Cámara → servidor | [api-dispositivo.md](api-dispositivo.md) y sus casos del recorte, [casos-recorte.json](casos-recorte.json) | 1.2 | B | A (firmware y simulador) |
| API REST | [openapi.yaml](openapi.yaml) | 1.4 | B | C (web), A (simulador) |
| MQTT y Home Assistant | [mqtt.md](mqtt.md) | 1.3 | B | A (placa y simulador), C (Home Assistant) |
| Agente (MCP) | [mcp-agente.md](mcp-agente.md) | 1.2 | B | C (Home Assistant) |
| Base de datos | [base-de-datos.sql](base-de-datos.sql) | 1.2 | B | B (servidor y MCP) |

## Cómo cambia un contrato

1. Quien necesita el cambio lo propone en un PR que toca el contrato y explica por qué. La rama lleva el prefijo `b/`, porque el frente B es el dueño de los contratos (por ejemplo, `b/contratos-v1-1`).
2. Lo aprueban los frentes que lo usan.
3. Sube la versión: 1.1 si solo agrega algo compatible (un campo opcional, una ruta nueva); 2.0 si rompe algo (cambia o quita un campo, un tema o un código).
4. Se anota en el registro de cambios de `../decisiones.md`; si rompe algo, también en la bitácora.
5. Después cambia el código, con sus pruebas de contrato al día.

## Pruebas de contrato

Cada contrato tiene pruebas con la marca `contrato <nombre> · <caso>`:

- Servidor: cada respuesta y error de `api-dispositivo.md`, cada tema MQTT, cada herramienta del agente, el esquema migrado igual a `base-de-datos.sql` y las respuestas de la API validadas contra `openapi.yaml`.
- Web: los tipos se generan desde `openapi.yaml`; si el contrato cambia y la web no, TypeScript no compila.
- Firmware y simulador: los casos de `casos-recorte.json` (marca `contrato recorte · <caso>`).
- Firmware: el mensaje Ambiente y el descubrimiento de la placa, sin placa (marcas `contrato MQTT · ambiente` y `contrato MQTT · descubrimiento de la placa`).
- Simulador: un modo que envía las fotos de `datos/prueba/` y compara las respuestas.

## `openapi.yaml` 1.4 y `mqtt.md` 1.3 (2026-11-12)

Dos agregados, propuestos en la tarea B2 del Día 3. Los demás contratos no cambian.

- `openapi.yaml` 1.4: `EstadoCamara` suma `sensor` (`dht22` o `dht11`) y `antena` (`interna` o `externa`), opcionales, como ya decía `mqtt.md` 1.2. La API devuelve solo los campos que mandó la cámara. La web regenera sus tipos con `npm run tipos`.
- `mqtt.md` 1.3: cada vez que se conecta al broker, el servidor borra los config que publicó para cámaras que ya no existen en la base. Los de la placa se siguen borrando a mano.
- Los dos solo agregan, por eso son 1.4 y 1.3 y no 2.0. `openapi.yaml` 1.4 pasa `openapi-spec-validator` (OpenAPI 3.1).

## Cámara → servidor 1.2 (2026-11-12)

Una aclaración en `api-dispositivo.md`, propuesta en la tarea B2 del Día 2. Los demás contratos no cambian.

- 100 KB son 102 400 bytes: el servidor responde 413 `imagen_grande` desde 102 401 bytes. El simulador ya envía como máximo 100 000 bytes, así que los dos lados quedan de acuerdo.
- Solo aclara: no cambia campos, códigos ni temas, por eso es 1.2 y no 2.0. Los casos de `casos-recorte.json` no cambian.

## `mqtt.md` 1.2 (2026-11-12)

Por el hardware real de la clase (D-21): una XIAO ESP32-C6 con un sensor de temperatura y humedad, y Home Assistant OS en la Pi. Solo agrega, por eso es 1.2 y no 2.0. Los demás contratos no cambian, y `api-dispositivo.md` y `openapi.yaml` no se tocan.

- Tema `accesia/{codigo}/ambiente`, con el mensaje Ambiente: temperatura y humedad cada 30 s, retenido, y `null` tras 3 lecturas fallidas seguidas.
- La placa publica el descubrimiento de sus dos sensores de ambiente, para que se vean aunque el servidor esté apagado. El servidor sigue publicando el de las demás entidades.
- La ACL de `camara` suma tres líneas `pattern` para esos temas. El archivo `infra/mosquitto/acl` y su prueba `contrato MQTT · acl` se actualizan aparte, con la lista de infra de D-21.
- `EstadoCamara` suma `sensor` y `antena`, los dos opcionales; la XIAO ESP32-C6 no envía `psram_kb`.
- El broker de la demo es el Mosquitto del portátil, en la IP del hotspot de Windows.

## Versión 1.3 (2026-11-12)

Dos agregados en `openapi.yaml`, propuestos en la tarea B1 del Día 2. Los demás contratos no cambian.

- `Error.codigo` suma `metodo_no_permitido`: una ruta que existe, llamada con otro método, responde 405 con ese código. Antes respondía `no_encontrado`, que no describía el error.
- `Dispositivo` suma `inscripcion_activa`, siempre presente: la inscripción activa de la cámara como `InscripcionCorta`, o `null`, después de vencer las que ya pasaron su hora (R9). Así la web la encuentra aunque haya perdido su id, por ejemplo ante un 409 `inscripcion_activa`. `modo` es `inscribir` si y solo si el campo no es `null`.
- Los dos solo agregan: nada de lo que ya existía cambia, por eso es 1.3 y no 2.0.
- `openapi.yaml` 1.3 pasa `openapi-spec-validator` (OpenAPI 3.1).

## Versión 1.2 (2026-11-11)

Horarios por bloques (D-20) en `base-de-datos.sql`, `openapi.yaml` y `mcp-agente.md`. `api-dispositivo.md` y `mqtt.md` siguen en 1.1.

- `openapi.yaml` 1.2 pasa `openapi-spec-validator` (OpenAPI 3.1).
- `base-de-datos.sql` 1.2 cargó en PostgreSQL 18.6 con pgvector, y pasaron estas comprobaciones:
  - «Clase IA» queda con cinco bloques;
  - solo puede haber un bloque por horario y día, y el día va de 1 a 7;
  - un horario en uso no se borra, y al borrar uno se borran sus bloques;
  - `v_persona_agente` saca los días de los bloques, y el usuario `agente` no lee `horario_bloque`;
  - los tres casos nuevos de R5 dan el resultado esperado.
- Borrar un horario en uso falla con `restrict_violation` (SQLSTATE 23001), no con `foreign_key_violation`: el servidor debe traducirlo a 409 `horario_en_uso`.

## Versión 1.1 (2026-11-11)

Acuerdos de la tarea 00 sobre la revisión `docs/revisiones/2026-11-11-revision-contratos-v1.md`. El detalle está en el registro de cambios de `../decisiones.md`.

- `openapi.yaml` 1.1 pasa `openapi-spec-validator` (OpenAPI 3.1).
- `base-de-datos.sql` 1.1 cargó en PostgreSQL 18.6 con pgvector real (`pgvector/pgvector:pg18`), con pruebas de las restricciones nuevas y de los permisos del usuario `agente`. La prueba con la migración y testcontainers sigue siendo de la tarea B del Día 1.
- Los casos de `casos-recorte.json` cumplen la fórmula de `api-dispositivo.md`.

## Revisión al crear el kit (2026-11-11)

- `openapi.yaml` pasa `openapi-spec-validator` (OpenAPI 3.1).
- `base-de-datos.sql` se cargó en un PostgreSQL 16 de prueba, con `vector` y `uuidv7` simulados. Se comprobaron las restricciones, las vistas del agente, que el usuario `agente` solo puede leer esas vistas y el borrado en cascada.
- Falta cargarlo en PostgreSQL 18 con pgvector real: lo hace la tarea B del Día 1.
