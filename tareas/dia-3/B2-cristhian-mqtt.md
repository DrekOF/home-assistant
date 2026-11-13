<!--
Nombre: B2-cristhian-mqtt.md
Descripción: Tarea B2 del Día 3 del frente B: el servidor en MQTT. Disponibilidad, descubrimiento de Home Assistant (con el model de D-21 y su limpieza), eventos (con la repetición de R4), alertas de R6, resumen y el estado de las cámaras.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Frente B · B2 · El servidor en MQTT

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/mqtt`
- Depende de:
  - B1 del Día 3 en `main`, por la llegada que viaja en el Evento y por el resumen;
  - el PR #11, ya en `main`, con la ACL 1.1 y sus casos en `test_mqtt_acl.py`.
- Lee primero: `CLAUDE.md`; `tareas/dia-3/00-todos-orden-e-hito-2.md`; `specs/contratos/mqtt.md` completo; `specs/reglas.md` (R4 y R6); `specs/requisitos.md` (RF-07 · C1 a C3, RNF-03 · C2); `specs/arquitectura.md` (Flujos y Servicios de Docker Compose, un solo proceso); `specs/decisiones.md` (D-05, D-18 y D-21); `servidor/README.md`.

## Objetivo

El servidor publica en MQTT lo que dice `mqtt.md` 1.2:

- su disponibilidad;
- el descubrimiento de las entidades de Home Assistant;
- cada evento, también la repetición de un `permitido`;
- las alertas de R6 y el resumen.

También escucha la disponibilidad y el estado de las cámaras. Con esto Home Assistant abre la puerta y avisa de desconocidos (Hito 2).

## Antes de empezar

- `paho-mqtt` 2.x pasa a las dependencias del servidor (hoy solo está en las de pruebas). `MQTT_URL` ya la arma Compose.
- Propón en el plan:
  - el client id del servidor y cómo se reconecta sin frenar las respuestas a la cámara;
  - cuándo se publica el Evento: después de confirmar la transacción, para que Home Assistant nunca vea un evento deshecho, y sin demorar la puerta más de lo necesario (RNF-03 · C2, menos de 2 s);
  - dónde vive la hora de la última alerta de R6: en memoria (`reglas.md` lo permite), con un solo proceso;
  - qué `model` lleva una cámara de tipo `simulador`; el de la placa es «XIAO ESP32-C6» (paso 2);
  - la limpieza del descubrimiento (paso 2): cuándo se hace y cómo se reconocen los config que sobran;
  - cómo se llenan `en_linea` y `estado` de las cámaras con `accesia/{codigo}/disponible` y `accesia/{codigo}/estado` (pendiente de B1 del Día 2), y qué pasa si el broker no está;
  - si `EstadoCamara` suma `sensor` y `antena` en `openapi.yaml`, como ya dice `mqtt.md` 1.2. Sería la versión 1.4, solo agrega: va en este PR con su registro, y se regeneran los tipos de la web con `npm run tipos`.

## Hacer

1. Conexión (`mqtt.md`, Broker y Temas):
   - con el usuario `servidor`, como parte del arranque y sin impedirlo si el broker no responde;
   - último deseo: `offline`, retenido, en `accesia/servidor/disponible`; `online` al conectarse;
   - `GET /api/v1/salud` dice `mqtt` `ok` o `sin_conexion`, y `estado` `ok` solo con la base y MQTT bien.
2. Descubrimiento (`mqtt.md`, Entidades de Home Assistant):
   - las seis entidades de cada cámara y las cuatro del servidor, con `default_entity_id`, disponibilidad y `device`;
   - se publica al arrancar, cuando Home Assistant publica `online` en `homeassistant/status` y cuando se crea o se cambia una cámara (por la API o con `crear-camara`);
   - el `model` del dispositivo es «XIAO ESP32-C6» (D-21). Quedó pendiente de la lista de infra de D-21;
   - limpieza, también pendiente de esa lista:
     - los config retenidos que el servidor publicó para cámaras que ya no existen se borran con un mensaje vacío retenido;
     - Home Assistant no debe mostrar dispositivos de cámaras borradas;
     - si eso cambia lo que dice `mqtt.md`, donde hoy los de una placa retirada se borran a mano, se propone la 1.3 en el PR;
   - no se pisan ni se borran los config de la placa: los de Temperatura y Humedad son de ella (D-21).
3. Evento (`accesia/{codigo}/evento`, QoS 1, no retenido):
   - cada `permitido`, `denegado` o `desconocido` guardado, con `asistencia` cuando ese evento creó la llegada del día;
   - la repetición de un `permitido` se publica con `repetido: true`, el `evento_id` original y la persona, la similitud y la hora de este recorte; la de un `denegado` no se publica (R4);
   - un `desconocido` nunca dice a quién se parece.
4. Alerta de R6 (`accesia/{codigo}/alerta`): los siete casos de R6. Cuentan los desconocidos de esa cámara de hace menos de `ALERTA_VENTANA_S` y posteriores a su última alerta, con una sola alerta por ventana.
5. Resumen (`accesia/resumen`, retenido):
   - se publica al arrancar, después de cada evento guardado, después de cada llegada manual (B1) y cada 5 minutos;
   - así cambia de día a medianoche.
6. Cámaras:
   - escucha `accesia/+/disponible` y `accesia/+/estado` para `en_linea` y `estado` de `GET /api/v1/dispositivos`;
   - descarta los mensajes que no cumplen EstadoCamara.
7. Pruebas con Mosquitto en un contenedor, como `test_mqtt_acl.py`, cada una con su marca:

   | Marca | Casos |
   | --- | --- |
   | `contrato MQTT · <tema>` | Cada tema que publica el servidor, con su QoS, su retención y su mensaje validado contra `mqtt.md` |
   | `contrato MQTT · repetido` | Un `permitido` repetido se publica con `repetido: true`; un `denegado` repetido no |
   | `R4 · dentro` y `R4 · denegado repetido` | La parte de MQTT que quedó pendiente en B2 del Día 2 |
   | `R6 · <caso>` | Los siete de R6, con el reloj de las pruebas |
   | `RF-07 · C1` | El descubrimiento al arrancar, con `homeassistant/status` `online` y al crear una cámara, con el `model` de D-21 |
   | `contrato MQTT · limpieza del descubrimiento` | Los config de una cámara que ya no existe se borran; los de la placa no |
   | `RF-10 · C3` | En línea y estado de la cámara desde MQTT |

8. `servidor/README.md`, `infra/README.md` (cómo mirar el tráfico) y, si cambia, `arquitectura.md`.

## No hacer

- No configures Home Assistant: es de C2.
- No toques `infra/mosquitto/acl`, `firmware/` ni `simulador/`.
- No publiques imágenes ni a quién se parece una cara (RNF-01 · C3).
- No inventes temas ni campos: los cambios de `mqtt.md` u `openapi.yaml` se proponen en el PR.

## Criterios de aceptación

- C1 (RF-07 · C1) Las entidades aparecen solas al arrancar el servidor y cuando Home Assistant avisa que está en línea, con el `model` «XIAO ESP32-C6», y no quedan las de cámaras que ya no existen.
- C2 (R4; `mqtt.md` · Temas) Cada evento guardado y cada `permitido` repetido se publican; un `denegado` repetido no.
- C3 (R6; RF-07 · C3) Los siete casos de R6 pasan y la alerta sale con su mensaje.
- C4 (`mqtt.md` · Mensajes) El Evento, la Alerta, el Resumen y el descubrimiento cumplen el contrato, con su QoS y su retención.
- C5 (RF-10 · C3) `en_linea` y `estado` de las cámaras salen de MQTT, y la salud dice si MQTT está conectado.
- C6 (RNF-06 · C3) `uv run pytest` y `servidor.yml` en verde; si cambia `openapi.yaml`, también `web.yml`.
- C7 `servidor/README.md`, las specs y la bitácora al día.

## Al terminar

- Resume:
  - qué hiciste y qué pruebas corriste, con su resultado por marca;
  - qué decidiste (client id, momento de publicar, `model` del dispositivo, limpieza del descubrimiento y `EstadoCamara`).
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con todos los workflows del PR en verde. Cuando esté en `main`, avisa a C para C2.
- El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
