<!--
Nombre: A-julian-simulador.md
Descripción: Tarea del Día 2 del frente A: simulador de la cámara con YuNet, la fórmula del recorte, el envío del contrato y el modo «como la cámara».
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 2 · Frente A · Simulador de la cámara

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/simulador`
- Lee primero: `CLAUDE.md`; `tareas/dia-2/00-todos-orden-e-hito-1.md`; `specs/arquitectura.md` (Simulador, y Firmware de la cámara · Comportamiento); `specs/contratos/api-dispositivo.md` completo, con la fórmula del recorte y «Qué hace la cámara con la respuesta»; `specs/contratos/casos-recorte.json`; `specs/requisitos.md` (RF-01, RNF-01 y RNF-07); `specs/reglas.md` (R7, por el puntaje de YuNet y el tamaño mínimo); `specs/decisiones.md` (D-02 y D-10); `tareas/dia-1/A-julian-esp-idf-y-deteccion.md` (las pruebas que el simulador comparte con el firmware).

## Objetivo

Un simulador en `simulador/` que hace lo mismo que la cámara, con la webcam o con una carpeta de fotos: detecta con YuNet, recorta con la fórmula del contrato y envía cada recorte al servidor según `api-dispositivo.md`. Tiene el modo «como la cámara», para que los recortes se parezcan a los del ESP32-S3. La puerta por MQTT queda para el Día 3.

## Antes de empezar

- Fija el modelo YuNet: `face_detection_yunet_2023mar.onnx` de `opencv/opencv_zoo`, en un commit fijo y con su SHA-256.
  - opencv_zoo guarda los modelos con Git LFS: `raw.githubusercontent.com` devuelve el puntero de LFS y no el modelo. Descárgalo de `https://github.com/opencv/opencv_zoo/raw/<commit>/models/face_detection_yunet/face_detection_yunet_2023mar.onnx` y comprueba el hash.
  - YuNet 2023mar pide OpenCV 4.8 o más reciente.
  - Si B2 ya anotó la URL y el hash de YuNet en `specs/arquitectura.md` (Piezas), usa esos. Si no, anótalos tú ahí: B2 usará los mismos.
- Propón en el plan el formato del archivo de respuestas esperadas del modo carpeta (Hacer, punto 5). El contrato dice que ese modo existe, pero no cómo se escribe lo esperado.
- Propón en el plan cómo queda en 320 × 240 una imagen que no es 4:3 (Hacer, punto 2).

## Hacer

1. Proyecto `simulador/` con uv y Python 3.13, como el servidor:
   - Dependencias: `opencv-python` (con ventanas, para la webcam), `numpy` y `httpx`. Para pruebas, `pytest`. `paho-mqtt` llega el Día 3, con la puerta.
   - Paquete `simulador` con el comando `simulador` (`uv run simulador …`).
   - El modelo se descarga la primera vez a `datos/modelos/`, se comprueba con su SHA-256 y nunca se sube: Git y Docker ya ignoran `datos/`. En clase no hay internet (RNF-04 · C3); el kit del Día 4 lleva el modelo.
2. Lógica común a los dos modos, sin cámara ni servidor, para poder probarla:
   - Modo «como la cámara» (`--como-camara`): antes de detectar, reduce la imagen a 320 × 240 y la pasa por JPEG de calidad 80 (`arquitectura.md`, Simulador).
     - Una webcam de 1280 × 720 es 16:9 y la cámara es 4:3: reducirla sin más deforma la cara.
     - Propón en el plan cómo llevarla a 320 × 240 sin deformarla (por ejemplo, recortar al centro a 4:3 y después reducir) y anótalo en `arquitectura.md`, sección Simulador.
   - Detección con YuNet (`cv2.FaceDetectorYN`), con umbral de puntaje 0,9 por defecto, el del paso 1 de R7.
   - Descarta las caras de menos de `--cara-min` píxeles de alto (80 por defecto, igual que `CARA_MIN_PX`). Sin cara no envía nada (RF-01 · C3).
   - Elige la cara de mayor área y la recorta con la fórmula de `api-dispositivo.md`: piso al inicio, techo al final y cortado en los bordes del cuadro.
   - Comprime el recorte en JPEG de calidad 80. Si pasa de 100 KB, no lo envía y lo dice en la consola, porque el contrato no lo permite.
3. Envío según `api-dispositivo.md`:
   - `POST {servidor}/api/v1/dispositivos/{codigo}/rostros` con `Authorization: Bearer <token>`, `Content-Type: image/jpeg`, `X-AccesIA-Firmware: simulador-<versión>` y `X-AccesIA-Puntaje` con el puntaje de YuNet.
   - El token sale de la variable `TOKEN_CAMARA`, como en el ejemplo del contrato. Nunca va en un archivo del repositorio ni en la salida. El servidor va en `--servidor` (por defecto `http://localhost:8000`) y el código de la cámara en `--codigo`.
   - Esperas, contadas desde que llega la respuesta:

     | Respuesta | Espera antes del siguiente recorte |
     | --- | --- |
     | `descartado`, `muestra_aceptada` o `muestra_rechazada` | Al menos 1 s |
     | `permitido`, `denegado` o `desconocido` | 3 s |
     | 401 o 403 | 30 s |
     | 429 | Lo que diga `Retry-After` |
     | Sin respuesta en 5 s, o 5xx | 1, 2, 4 y hasta 10 s |

   - Muestra cada respuesta en una línea: resultado, motivo, persona, similitud, `repetido` y, en modo inscribir, «Muestra 3 de 5».
4. Modo webcam: `uv run simulador webcam --codigo entrada [--como-camara] [--camara 0]`.
   - Abre una ventana con la imagen, la caja de la cara elegida y el último mensaje del servidor.
   - Se cierra con `q` o Esc.
   - No guarda cuadros ni recortes.
5. Modo carpeta, para pruebas repetibles: `uv run simulador carpeta datos/prueba --codigo entrada [--como-camara]`.
   - Envía cada foto, en orden por nombre, con las mismas esperas.
   - Si la carpeta trae el archivo de respuestas esperadas (con el formato acordado en el plan), compara cada respuesta, muestra un resumen y termina con código 1 si alguna no coincide.
   - Es el modo que pide `api-dispositivo.md` (Pruebas de contrato) y el que usará la calibración del Día 4 (RNF-07).
6. Pruebas con pytest, cada una con su marca, sin fotos de caras en el repositorio:

   | Marca | Qué comprueba |
   | --- | --- |
   | `contrato recorte · <caso>` | Los casos de `casos-recorte.json`, leídos del archivo: cara elegida, `(x0, y0)`, `(x1, y1)` y tamaño |
   | `RF-01 · C6 · cara mínima` | No envía si no hay cara ni si la cara mide menos de `cara_min` |
   | `RF-01 · C6 · espera` | Espera 1 s desde la respuesta, y 3 s tras `permitido`, `denegado` o `desconocido` (con un reloj falso) |
   | `contrato cámara · cabeceras` | El envío lleva las cuatro cabeceras y el cuerpo es un JPEG de 100 KB o menos |
   | `contrato cámara · respuestas` | 401 y 403 esperan 30 s; 429, `Retry-After`; sin respuesta o 5xx, 1, 2, 4 y hasta 10 s (servidor falso con `httpx.MockTransport`) |
   | `RNF-07 · como la cámara` | El modo deja la imagen en 320 × 240, sin deformarla, y la pasa por JPEG 80 antes de detectar |
   | `RNF-01 · C1` | Ningún modo escribe imágenes: la prueba falla si se llama a `cv2.imwrite` o aparece un archivo de imagen |

   Las pruebas que necesitan caras reales leen `datos/prueba/` y, si la carpeta no existe, se saltan diciendo por qué.
7. `simulador/README.md`: instalación, comandos, formato de las respuestas esperadas (con un ejemplo inventado, sin datos reales) y cómo correr las pruebas. La sección «Comandos» de `CLAUDE.md` suma los del simulador.

## No hacer

- Nada de MQTT ni de la puerta: el simulador todavía no se conecta a Mosquitto (Día 3).
- No guardes imágenes: ni cuadros, ni recortes, ni fotos para depurar. Las fotos de prueba del equipo viven solo en `datos/` (`CLAUDE.md`).
- No subas el modelo ONNX ni el token.
- No toques `firmware/` (la tarea A del Día 1 sigue abierta), `servidor/` ni `web/`.
- No cambies los contratos. Si algo no encaja, propón el cambio como dice `specs/contratos/README.md`.
- No crees un workflow de GitHub Actions: según RNF-06 · C3, el frente A se suma a la CI el Día 4 con `firmware.yml`. Si el equipo quiere un `simulador.yml` antes, se propone en el PR y se ajusta RNF-06 · C3.
- No calibres el umbral: RNF-07 es del Día 4.

## Criterios de aceptación

- C1 (RF-01 · C6 · `casos-recorte.json`) Las pruebas de los casos del recorte pasan leyendo el archivo, los mismos casos que usa el firmware.
- C2 (RF-01 · C2 y C3, en el simulador) No envía sin cara ni con caras menores que `cara_min`, y espera 1 s o 3 s desde cada respuesta.
- C3 (`api-dispositivo.md` · Petición y «Qué hace la cámara con la respuesta») Las cabeceras, el cuerpo y la reacción a cada respuesta y a cada error tienen su prueba.
- C4 (`arquitectura.md` · Simulador, RNF-07) `--como-camara` funciona en los dos modos y no deforma las imágenes 16:9.
- C5 (`api-dispositivo.md` · Pruebas de contrato) El modo carpeta compara con las respuestas esperadas y termina con código 1 si alguna no coincide.
- C6 (RNF-01 · C1) Ningún modo escribe imágenes, con su prueba en verde.
- C7 (RF-01 · C6, de punta a punta) Contra el servidor real, con la cámara `entrada` de tipo `simulador`, el modo webcam recibe `permitido`, `desconocido` y, durante una inscripción, `muestra_aceptada`. Se comprueba cuando B2 esté en `main`, a más tardar en el Hito 1.
- C8 `uv run pytest` en verde en `simulador/`; `simulador/README.md`, `CLAUDE.md` y la bitácora al día.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado, cómo quedó el modo «como la cámara» con imágenes 16:9 y qué queda para el Día 3 (MQTT y la puerta).
- Agrega la entrada de la tarea en `docs/bitacora.md`: qué, quién, cómo (con el método con IA), pruebas, cambios de specs y pendientes. Incluye el commit de opencv_zoo y el SHA-256 de YuNet.
- Si cambiaste `arquitectura.md` (modelo o modo «como la cámara»), sube su versión y su fecha.
- PR a `main` con la etiqueta `frente-a`. Se fusiona con las pruebas en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
