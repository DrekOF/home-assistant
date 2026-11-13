<!--
Nombre: A3-julian-ip-de-la-pi.md
Descripción: Tarea A3 del Día 4 del frente A: los valores de fábrica del firmware y los ejemplos del simulador pasan del portátil a la IP fija de la Raspberry Pi (D-22).
Fecha de creación: 2026-11-13
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 4 · Frente A · A3 · La IP de la Pi en la placa y el simulador

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/ip-de-la-pi`
- Depende de:
  - D-22 en `main` (PR #20);
  - la IP fija de la Pi en el hotspot, que se confirma en clase (P-04). Mientras tanto se usa la del ejemplo de D-22, `192.168.137.250`, y si en clase es otra, se cambia en un solo lugar;
  - nada de B ni de C. No necesita la placa ni la Pi.
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/decisiones.md`: D-21, D-22 y «Cómo se aplica D-22» (Red);
  - de `specs/arquitectura.md`: Firmware (la placa de la demo y su consola), Simulador y Red y despliegue;
  - de `specs/requisitos.md`: RF-14 · C1 y C6;
  - `firmware/README.md` (la consola y los valores de fábrica) y `simulador/README.md` (`--servidor`, `--broker` y los ejemplos).

## Objetivo

Con D-22, el servidor y el broker de la demo están en la Pi. Los valores de fábrica del firmware y los ejemplos del simulador pasan del portátil (`192.168.137.1`, D-21) a la IP fija de la Pi:

- la API en `http://<IP de la Pi>:8000`;
- MQTT en `mqtt://<IP de la Pi>:1883`.

Así, una placa recién flasheada se conecta a la Pi sin pasar por la consola. Para el plan B (el escenario 2), se vuelve al portátil con la consola o con las opciones del simulador, sin recompilar (RF-14 · C6).

## Antes de empezar

- Propón en el plan:
  - qué cambia en `firmware/`: los valores por defecto de `firmware/components/accesia_config/include/accesia/config.hpp` y los ejemplos de la consola;
  - qué cambia en el simulador: los ejemplos de `simulador/README.md` y los valores por defecto que apunten al hotspot. Lo que apunta a `localhost` es para desarrollar con el Compose del portátil y puede quedarse;
  - cómo se cambia la IP en un solo lugar si P-04 confirma otra;
  - qué pruebas lo cubren, en la lógica pura del firmware y en el simulador.

## Hacer

1. Los valores de fábrica y los ejemplos de la consola del firmware, con sus pruebas si las tocan.
2. Los ejemplos y los valores del simulador que apunten al hotspot, con sus pruebas.
3. La documentación:
   - `firmware/README.md`, `simulador/README.md` y los pasos de la placa y del simulador en `docs/guia-dia-de-clase.md`;
   - en `specs/arquitectura.md` (Firmware), quitar que «mientras el firmware no cambie» se ajustan con la consola;
   - la bitácora.

## No hacer

- No cambies el contrato MQTT, la API ni la lógica del firmware: solo valores y ejemplos.
- No toques `servidor/`, `web/` ni `infra/`.
- No subas binarios: el del kit se arma en A2, después de esta tarea.

## Criterios de aceptación

- C1 (D-22) Con los valores de fábrica, la placa apunta a la Pi, y el simulador y sus ejemplos también.
- C2 (RF-14 · C6) Con la consola, la placa vuelve al portátil sin recompilar, y el simulador con sus opciones.
- C3 (RF-14 · C1; RNF-06 · C3) `firmware.yml` y `simulador.yml` en verde.
- C4 Los README, la guía, `arquitectura.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué valores y ejemplos cambiaron;
  - cómo se cambia la IP si en clase es otra;
  - qué pruebas corriste, con su resultado.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-a`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
