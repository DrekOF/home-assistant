<!--
Nombre: A1-julian-puerta-del-simulador.md
Descripción: Tarea A1 del Día 3 del frente A: el simulador se conecta a MQTT como una cámara y simula la puerta (ABRIR y CERRAR), sin chocar con la XIAO ESP32-C6 que usa el mismo código.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Frente A · A1 · La puerta del simulador por MQTT

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/puerta-simulador`
- Depende de: nada del servidor. Solo necesita el broker de Docker Compose y el usuario `camara` con su clave de `infra/.env`; la ACL ya está en `main`.
- Lee primero: `CLAUDE.md`; `tareas/dia-3/00-todos-orden-e-hito-2.md`; `specs/contratos/mqtt.md` completo (Broker, Temas, EstadoCamara y Entidades); `specs/arquitectura.md` (Simulador y Red y despliegue); `specs/decisiones.md` (D-10 y D-21); `specs/requisitos.md` (RF-07 · C2 y RNF-03 · C2); `simulador/README.md`.

## Objetivo

El simulador también hace la parte MQTT de la cámara: con su código como client id, recibe `ABRIR` y `CERRAR`, muestra «PUERTA ABIERTA» 3 s, publica el estado de la puerta, su estado general y su disponibilidad. Así el Hito 2 se puede hacer aunque la placa no esté a mano, y sin chocar con ella cuando sí está.

## Antes de empezar

- La placa y el simulador no pueden conectarse a la vez con el mismo client id (`mqtt.md`, Broker). En la demo la placa maneja la puerta de `entrada`, y el simulador envía los recortes de `entrada` por HTTP.
- Propón en el plan:
  - cómo se activa MQTT en el simulador. Por ejemplo, una opción `--puerta` que lo conecte, apagada por defecto para que no le quite la conexión a la placa;
  - de dónde salen la dirección del broker y la clave del usuario `camara`: una opción o una variable de entorno, nunca en el código ni en la línea de comandos que queda en el historial;
  - cómo se ve «PUERTA ABIERTA» en el modo webcam (en la ventana) y en el modo carpeta (en la consola);
  - qué pasa con un `ABRIR` que llega con la puerta abierta y con un mensaje que no es `ABRIR` ni `CERRAR`. El contrato no lo dice: usa lo mismo que decidió la placa en el PR #11, para que las dos se comporten igual.
- `paho-mqtt` 2.x, que ya usa el servidor en sus pruebas. Antes de agregar otra librería, pregunta.

## Hacer

1. Conexión (`mqtt.md`, Broker y Temas):
   - El client id es el código de la cámara y el usuario es `camara`; la ACL lo exige.
   - Último deseo: `offline`, retenido, en `accesia/{codigo}/disponible`. Al conectarse publica `online`, retenido, con QoS 1.
   - Reintenta si el broker no está, sin detener el envío de recortes: la puerta nunca frena el reconocimiento.
2. Puerta (`mqtt.md`, Temas):
   - Se suscribe a `accesia/{codigo}/puerta/set`.
   - Con `ABRIR`, muestra «PUERTA ABIERTA» los segundos configurados (3 por defecto) y publica `abierta` y después `cerrada` en `accesia/{codigo}/puerta/estado`, retenidos y con QoS 1.
   - `CERRAR` la cierra antes.
3. Estado general: cada 60 s publica EstadoCamara en `accesia/{codigo}/estado`, retenido y con QoS 0. Lleva `firmware` (el mismo texto de `X-AccesIA-Firmware`), `ip` y `segundos_encendida`, sin `perfil`, `rssi`, `psram_kb` ni `libre_kb` (`mqtt.md`, EstadoCamara).
4. Al salir (q, Esc o Ctrl+C), publica `offline` y cierra la conexión; si se corta de golpe, queda el último deseo.
5. Pruebas, cada una con su marca:
   - `contrato MQTT · puerta`: `ABRIR` publica `abierta` y luego `cerrada` a los segundos configurados; `CERRAR` la cierra antes.
   - `contrato MQTT · disponible`: el último deseo y el `online` al conectarse.
   - `contrato MQTT · estado del simulador`: los campos de EstadoCamara que manda el simulador, y solo esos.
   - Que sin la opción de MQTT el simulador no se conecta al broker.
   - Con un broker falso o con Mosquitto en un contenedor (como `test_mqtt_acl.py` del servidor), para que corran en `simulador.yml`.
6. Prueba de punta a punta con el Compose de la carpeta principal (acuerdos de `00-todos-orden-e-hito-2.md`):
   - con `mosquitto_pub` y el usuario `homeassistant`, `ABRIR` en `accesia/entrada/puerta/set`;
   - el simulador lo muestra, y `mosquitto_sub` ve `abierta` y `cerrada`.
7. `simulador/README.md` (opción nueva, variables y ejemplo) y la sección Comandos de `CLAUDE.md`.

## No hacer

- No toques `firmware/`, `servidor/`, `web/` ni `infra/`. La ACL es del PR #11.
- No inventes temas ni campos: si algo no encaja, propón el cambio de `mqtt.md` como dice `specs/contratos/README.md`.
- No guardes imágenes ni la clave del broker.
- No calibres el umbral: RNF-07 es del Día 4.

## Criterios de aceptación

- C1 (`mqtt.md` · Temas) El simulador recibe `ABRIR` y `CERRAR`, y publica la puerta, su estado y su disponibilidad con la QoS y la retención del contrato.
- C2 (`mqtt.md` · Broker; D-21) Sin la opción de MQTT no se conecta, y la placa conserva la puerta de su código.
- C3 (RF-07 · C2) Con el Compose arriba, un `ABRIR` publicado a mano abre y cierra la puerta del simulador.
- C4 (RNF-01 · C1) Sigue sin escribir imágenes.
- C5 `uv run pytest` y `simulador.yml` en verde, con las marcas nuevas; `simulador/README.md`, `CLAUDE.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué hiciste y qué pruebas corriste, con su resultado;
  - cómo se activa MQTT;
  - cómo convive con la placa.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-a`. Se fusiona con `servidor.yml`, `web.yml` y `simulador.yml` en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
