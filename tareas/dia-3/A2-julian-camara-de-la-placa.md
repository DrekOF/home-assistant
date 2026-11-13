<!--
Nombre: A2-julian-camara-de-la-placa.md
Descripción: Tarea A2 del Día 3 del frente A, condicionada a que llegue el módulo de cámara (P-03): captura, TinyML y envío desde la placa, según arquitectura.md («Cuando llegue el módulo de cámara»).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Frente A · A2 · La cámara de la placa (cuando llegue el módulo)

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/camara-placa`
- Depende de:
  - que llegue el módulo de cámara (P-03). Si no llegó, la tarea no empieza: pasa al Día 4 y se anota en la bitácora;
  - el PR #11, ya en `main`, con el firmware del C6 y su punto de extensión `accesia_vision`;
  - si el módulo es una cámara SPI para el C6, el cambio de contrato de «Antes de empezar», fusionado antes del código.
- Lee primero: `CLAUDE.md`; `tareas/dia-3/00-todos-orden-e-hito-2.md`; `specs/arquitectura.md` (Firmware, en especial «Cuando llegue el módulo de cámara» y «Referencia: ESP32-S3»); `specs/decisiones.md` (D-02, D-17 y D-21); `specs/requisitos.md` (RF-01 y RF-14); `specs/contratos/api-dispositivo.md` completo; `firmware/README.md`.

## Objetivo

La placa toma imágenes con el módulo que llegó y se las envía al servidor, de la forma que corresponde a ese módulo. El reconocimiento queda igual que con el simulador.

## Antes de empezar

- Identifica el módulo, con su modelo, su interfaz y su sensor, y anótalo en `specs/README.md`: P-03 pasa a resuelto. Después sigue el caso que corresponde de `arquitectura.md`.
- Caso 1, cámara SPI con salida JPEG conectada al C6:
  - Un cuadro QVGA en JPEG (10 a 20 KB) cabe en la SRAM.
  - El TinyML es un clasificador int8 de TensorFlow Lite Micro (`espressif/esp-tflite-micro`, como su ejemplo `person_detection`). Dice si hay alguien, no dónde está la cara.
  - Sin cajas, la placa no puede recortar ni medir `cara_min`, así que envía el cuadro completo cuando hay alguien.
  - Eso cambia `api-dispositivo.md` y `openapi.yaml`. El cambio va primero, en su propio PR, como dice `specs/contratos/README.md`: lo propone A, lo escribe el frente B, dueño de los contratos, y lo aprueban B y C.
  - El servidor lo implementa en su propia tarea con `recortar_cara_mas_grande` (`servidor/accesia/vision.py`), que ya detecta con YuNet en un cuadro completo y recorta con la fórmula del contrato.
- Caso 2, placa con cámara aparte:
  - Si es un ESP32-S3 con cámara, vuelve el firmware de referencia del PR #7 como otro target del mismo proyecto (`idf.py set-target esp32s3`), con D-17. El contrato no cambia.
  - Si es un ESP32-CAM, sirve como cámara de respaldo con el modo extraer del servidor (RF-10 · C4), que es del Día 4. Aquí solo se deja su servidor de imágenes (`GET /capture`).
- Propón en el plan el caso y sus pasos, qué dependencias se fijan (versión y lockfile, como `esp-idf-lib/dht` en el PR #11) y cómo se prueba sin la placa en la CI.

## Hacer

1. Fuente de cuadros y detector en `accesia_vision`, según el caso, sin tocar la lógica de la puerta ni del ambiente.
2. Envío por `api-dispositivo.md`, con la lógica de la espera que ya trajo el PR #11:
   - al menos 1 s desde cada respuesta, y 3 s después de `permitido`, `denegado` o `desconocido`;
   - reintentos ante 5xx o si no hay respuesta;
   - 401 y 403 cada 30 s, y lo que diga `Retry-After` ante un 429.
3. Consola: lo que el caso necesite (por ejemplo, el umbral del detector), sin recompilar (RF-01 · C4, RF-14 · C6).
4. Pruebas de la lógica pura con `firmware/scripts/probar-logica.sh`:
   - lo que se decide sin hardware;
   - en el caso del S3, los casos de `casos-recorte.json` (marca `contrato recorte · <caso>`).
5. Prueba con la placa, contra el servidor del portátil en el hotspot: `permitido` para una persona inscrita y `desconocido` para otra. Mide el tiempo de respuesta (RF-04 · C5) y anótalo. Para esto, el firewall del portátil también deja entrar el 8000 desde `192.168.137.0/24` (C2).
6. `firmware/README.md`, `specs/arquitectura.md` (Firmware y Piezas) y la bitácora.

## No hacer

- No cambies `api-dispositivo.md` ni `openapi.yaml` en este PR: el cambio de contrato va en el suyo, antes.
- No toques `servidor/`, `simulador/`, `web/` ni `infra/`.
- No guardes imágenes en la placa ni en el servidor, ni para depurar (RNF-01 · C1).
- No subas modelos que no tengan licencia libre ni binarios generados.

## Criterios de aceptación

- C1 (P-03) El módulo queda identificado en `specs/README.md` y el caso elegido en `arquitectura.md`.
- C2 (RF-01, según el caso) La placa envía lo que dice el contrato vigente: el recorte si detecta caras, o el cuadro completo si el contrato cambió. Respeta las esperas del contrato.
- C3 (RF-14 · C1) `firmware.yml` en verde: compila el binario y pasan las pruebas de la lógica pura.
- C4 (RF-04 · C5) Con la placa, una persona inscrita sale `permitido` y otra `desconocido`, con el tiempo de respuesta anotado.
- C5 (RNF-01 · C1) No se escriben imágenes.
- C6 `firmware/README.md`, las specs y la bitácora al día.

## Al terminar

- Resume:
  - qué módulo llegó y qué caso se siguió;
  - qué hiciste y qué pruebas corriste, con su resultado;
  - qué cambio de contrato hizo falta y el tiempo medido.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-a`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
