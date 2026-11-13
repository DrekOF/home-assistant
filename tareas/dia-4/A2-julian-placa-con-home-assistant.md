<!--
Nombre: A2-julian-placa-con-home-assistant.md
Descripción: Tarea A2 del Día 4 del frente A: la XIAO ESP32-C6 con Home Assistant OS y el broker del portátil (RF-14 · C2 a C6), la lista «Por verificar» del firmware, el tiempo de la puerta y el binario con su flasheo para el kit.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 4 · Frente A · A2 · La placa con Home Assistant

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/placa-home-assistant`
- Depende de:
  - C2 del Día 3 en `main`: Home Assistant OS en la Pi con el broker del portátil, el hotspot y el firewall;
  - el Compose de la carpeta principal reconstruido con B2 del Día 3, que publica los eventos;
  - el Hito 2, que es la primera vez que se ven juntas la placa y Home Assistant.
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/requisitos.md`, RF-14, RF-07 · C2, RNF-03 · C2 y RF-11 · C2;
  - de `specs/contratos/mqtt.md`, Temas y «Entidades que publica la placa»;
  - `firmware/README.md`, en especial la prueba con la placa y «Por verificar con la placa»;
  - de `simulador/README.md`, la opción `--puerta`;
  - de `docs/guia-dia-de-clase.md`, el paso 3.

## Objetivo

La placa, con el firmware de `main`, funciona con Home Assistant OS y el broker del portátil:

- la puerta;
- su estado y su disponibilidad;
- la temperatura y la humedad;
- la consola por los dos puertos;
- la antena.

Queda medido el tiempo de la puerta, y su binario y los pasos para flashearla quedan listos para el kit.

## Antes de empezar

- Propón en el plan:
  - el orden de las pruebas, de lo que no necesita a Home Assistant (consola, LED, sensor) a lo que sí (entidades, automatización);
  - cómo se mide el tiempo de la puerta (RNF-03 · C2): del recorte del simulador al LED encendido, con la hora del registro del servidor, el de Home Assistant y la consola de la placa;
  - de dónde sale el binario del kit:
    - `firmware.yml` lo compila pero no lo guarda como artefacto. Puede sumar ese paso, para que el kit tome el binario de la CI de `main`, o el binario se compila en el portátil con `.\firmware\scripts\compilar.ps1`;
    - en los dos casos, anota la versión y el commit.

## Hacer

1. Flashear la placa con el binario acordado y configurarla por la consola, sin recompilar (RF-14 · C6): Wi-Fi del hotspot, servidor, código `entrada`, token, MQTT, puerta, sensor y antena.
2. Con Home Assistant OS, cada criterio de RF-14:
   - C2, la antena: el conmutador al arrancar, la interna y la externa, y la señal con cada una;
   - C3, el sensor: lecturas cada 30 s, y `null` después de 3 fallas seguidas (por ejemplo, desconectando el DHT);
   - C4, el descubrimiento: Temperatura y Humedad aparecen aunque el servidor esté apagado, y quedan no disponibles si la placa se desconecta;
   - C5, la puerta: `ABRIR` desde el botón de Home Assistant y desde un `permitido` del simulador, con `abierta` y luego `cerrada`;
   - C6: la consola por el USB-C y por UART0.
3. La lista «Por verificar con la placa» de `firmware/README.md`. Lo que se confirme sale de la lista; lo que no, queda con su resultado.
4. La convivencia con el simulador, que quedó pendiente en A1 del Día 3: si alguien corre el simulador con `--puerta` y el código de la placa, la placa recupera su conexión cuando el simulador se va.
5. El tiempo de la puerta, con un `permitido` y con la repetición de R4: menos de 2 s (RF-07 · C2, RNF-03 · C2).
6. Para el kit, con C1 (RF-11 · C2): el binario del C6 con su versión, esptool, y los pasos de flasheo y configuración en el paso 3 de la guía del día de clase, con los comandos de PowerShell.
7. `firmware/README.md` y la bitácora.

## No hacer

- No cambies el contrato MQTT ni la ACL: si algo no encaja, se propone el cambio de `mqtt.md`.
- No toques `servidor/`, `web/` ni `infra/`. La parte de `.github/workflows/firmware.yml`, si se acuerda, sí.
- No subas binarios generados: el binario va en `kit/`, que Git ignora.

## Criterios de aceptación

- C1 (RF-14 · C2 a C6) Cada criterio comprobado con la placa y Home Assistant OS, con su resultado en la bitácora.
- C2 (RF-07 · C2; RNF-03 · C2) La puerta se abre en menos de 2 s con un `permitido` y con la repetición de R4, medido.
- C3 La lista «Por verificar» resuelta, o con lo que falta anotado.
- C4 (RF-11 · C2) El binario, esptool y los pasos de flasheo listos para el kit, con la versión y el commit del binario.
- C5 (RF-14 · C1) `firmware.yml` en verde si cambia el firmware o su workflow; `firmware/README.md`, la guía y la bitácora al día.

## Al terminar

- Resume:
  - qué se comprobó con la placa y qué quedó pendiente;
  - el tiempo de la puerta;
  - de dónde sale el binario del kit.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-a`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
