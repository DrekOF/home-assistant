<!--
Nombre: B2-cristhian-reconocimiento-e-inscripcion.md
Descripción: Tarea B2 del Día 2 del frente B: reconocimiento con YuNet + SFace + pgvector, reglas R1 a R4 y R7, e inscripción (R9).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 2 · Frente B · B2 · Reconocimiento e inscripción

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/reconocimiento`, creada desde `main` con B1 ya fusionada
- Lee primero: `CLAUDE.md`; `tareas/dia-2/00-todos-orden-e-hito-1.md`; `specs/contratos/api-dispositivo.md` completo; `specs/contratos/openapi.yaml` (`enviarRostro`, Inscripciones y sus esquemas); `specs/reglas.md` (R1 a R4, R7, R8 y R9); `specs/requisitos.md` (RF-02 · C4, RF-03, RF-04, RF-05 · C1 y C2, RNF-01 y RNF-03 · C1); `specs/modelo-datos.md` (La búsqueda central); `specs/arquitectura.md` (Piezas, Flujos y Servicios de Docker Compose); `specs/decisiones.md` (D-02, D-03, D-13 y D-14); `docs/revisiones/2026-11-11-revision-contratos-v1.md` (puntos 1.9, 1.10, 3.3, 3.4, 3.5 y 3.7); `servidor/README.md`.

## Objetivo

El servidor recibe el recorte de la cámara o del simulador, saca la huella con YuNet + SFace, la compara con pgvector y responde según el contrato. Si la cámara no tiene inscripción activa, reconoce con R1 a R4; si la tiene, guarda muestras con R7 y R9. MQTT, asistencia (R5) y alertas (R6) quedan para el Día 3.

## Antes de empezar

- Fija los modelos de `opencv/opencv_zoo` en un commit fijo y con su SHA-256: `face_detection_yunet_2023mar.onnx` y `face_recognition_sface_2021dec.onnx` (`arquitectura.md`, Piezas).
  - Si A ya anotó YuNet en `specs/arquitectura.md`, usa la misma URL y el mismo hash, y anota ahí SFace. Si no, anota los dos.
  - opencv_zoo los guarda con Git LFS: `raw.githubusercontent.com` devuelve el puntero de LFS y no el modelo. Usa `https://github.com/opencv/opencv_zoo/raw/<commit>/…` y comprueba el hash.
- OpenCV: `opencv-python-headless`, que no necesita librerías gráficas en la imagen, en versión 4.8 o más reciente (la pide YuNet 2023mar). Si se puede, la misma versión que el simulador.
- Propón en el plan:
  - los mensajes de la respuesta (`mensaje`): el contrato da ejemplos, no una lista. No hay dato de género, así que el saludo no puede depender de él;
  - qué responde `POST /api/v1/inscripciones` si la cámara está inactiva: R9 pide una cámara activa y el contrato no dice el código;
  - el orden de las comprobaciones de `enviarRostro` (token, tipo, tamaño, 429 e imagen).

## Hacer

1. Visión, con la imagen solo en memoria (RF-04 · C1 y C4):
   - Decodifica el JPEG con `cv2.imdecode`. Si no se puede leer: 422 `imagen_invalida`.
   - YuNet (`cv2.FaceDetectorYN`) sobre el recorte completo, con umbral de puntaje 0,9 (R7, paso 1).
   - SFace: `alignCrop` a 112 × 112 y `feature`, normalizada: 128 números.
   - Nitidez: varianza del laplaciano de la cara alineada, en gris (R7, paso 4).
   - Todo detrás de una interfaz que las pruebas puedan reemplazar, para probar las reglas con caras y huellas armadas, sin fotos.
   - Los modelos se cargan una vez, al arrancar.
   - En la imagen, el `Dockerfile` descarga los modelos al construir y comprueba su hash, para amd64 y arm64. En el PC y en la CI se descargan a `datos/modelos/` (Git y Docker ignoran `datos/`), y `servidor.yml` los guarda en caché.
   - Si necesitas una variable para la ruta de los modelos, agrégala a `arquitectura.md` (Configuración) y a `infra/.env.example`.
2. `POST /api/v1/dispositivos/{codigo}/rostros` (`enviarRostro`, `api-dispositivo.md`):
   - Token Bearer comparado por su SHA-256 con `hmac.compare_digest`. Si falta, no corresponde o no existe la cámara: 401 `token_invalido`, sin decir cuál de las tres. Cámara inactiva: 403 `dispositivo_inactivo`.
   - Cada petición con token válido actualiza `ultimo_contacto`.
   - 415 `tipo_no_soportado` si no es `image/jpeg`; 413 `imagen_grande` si pasa de 100 KB; 429 `demasiadas_peticiones` con `Retry-After: 1` si llegan dos recortes de esa cámara con menos de 0,8 s. El control del 429 vive en memoria: el servidor corre con un solo proceso (`arquitectura.md`).
   - La respuesta es `RespuestaRostro`, con todos los campos siempre presentes y `hora` con `-05:00` (R8).
   - Antes de decidir el modo, vence la inscripción de la cámara si ya pasó su hora, con la función de B1.
3. Reconocer (RF-04 · C2 y C3; R1 a R4; R7 al reconocer):
   - Usa la cara más grande. Si no hay cara o mide menos de 0,8 × `CARA_MIN_PX`: `descartado`, con `sin_cara` o `cara_pequena`, sin evento.
   - Busca con la consulta central de `modelo-datos.md`. Sin muestras: `desconocido` con similitud `null`. Bajo el umbral: `desconocido`, `bajo_umbral` y sin persona.
   - R3: `inactiva` gana a `sin_consentimiento`.
   - R4: si la misma persona, en la misma cámara y con el mismo resultado, tiene un evento guardado hace menos de `VENTANA_REPETIDO_S`, responde `repetido: true` con el `evento_id` original y no guarda nada. No aplica a los desconocidos.
   - Guarda `evento_acceso` con la hora de `accesia.tiempo.ahora()`, no con `now()` de la base, para que las pruebas controlen el reloj.
   - Ni `persona` ni `mensaje` dicen a quién se parece un desconocido (RNF-01 · C3).
4. Inscripción (RF-02 · C4, RF-03, R7, R9, D-13):
   - `POST /api/v1/inscripciones`:
     - Persona o cámara que no existe: 404.
     - Sin consentimiento vigente: 422 `sin_consentimiento`.
     - Antes de abrir, vence la activa de esa cámara si ya pasó su hora. Si sigue habiendo una activa: 409 `inscripcion_activa`.
     - `requeridas` es `INSCRIPCION_MUESTRAS` y `vence` es la hora de apertura más `INSCRIPCION_VENCE_S`.
   - `GET /api/v1/inscripciones/{inscripcion_id}` (la vence si ya pasó su hora) y `DELETE` (la cancela; si ya terminó, 409 `inscripcion_terminada`).
   - Con una inscripción activa, cada recorte de esa cámara pasa por los seis pasos de R7, en orden, y responde el primer motivo que falle.
     - El paso 5 busca solo entre las muestras de otras personas (`WHERE persona_id <> :persona`).
     - El paso 6, desde la segunda muestra, compara con la primera muestra aceptada de esta misma inscripción.
   - Una muestra aceptada guarda un `rostro` (huella, `fuente` igual al tipo de la cámara, `calidad` igual a la nitidez e `inscripcion_id`) y suma una muestra. Al llegar a `requeridas`, la inscripción queda `completada`. Una muestra rechazada guarda `ultimo_motivo`.
   - En modo inscribir, `persona` es siempre quien se inscribe, `similitud` y `evento_id` son `null`, e `inscripcion` trae el avance (`api-dispositivo.md`).
5. Pruebas primero en las reglas, cada una con su marca:

   | Marca | Casos |
   | --- | --- |
   | `R1 · <caso>` | Los 3 de R1 |
   | `R2 · <caso>` | Los 2 de R2 |
   | `R3 · <caso>` | Los 5 de R3; `revocado de punta a punta` usa la API de consentimiento de B1 |
   | `R4 · <caso>` | Los 6 de R4, sin la parte de MQTT, que es del Día 3 |
   | `R7 · <caso>` | Los 15 de R7 |
   | `R9 · <caso>` | Los 7 que B1 no probó; `revoca a mitad` suma que la siguiente cara se reconoce |
   | `contrato cámara · <caso>` | Cada fila de las tablas de resultados y de errores de `api-dispositivo.md` |
   | `RF-02 · C4` | Sin consentimiento vigente no se abre una inscripción |
   | `RF-04 · C1` | La huella tiene 128 números y norma 1 (SFace real sobre una imagen de 112 × 112 sin cara) |
   | `RF-05 · C1` y `C2` | Se guarda evento salvo en las repeticiones de R4 y en los descartados |
   | `RNF-01 · C1` | Procesar un recorte no escribe archivos ni registra la imagen: falla si se llama a `cv2.imwrite` o si el JPEG o su base64 aparece en los registros |
   | `RNF-01 · C3` | Un `desconocido` y un `parece_otra_persona` no nombran a nadie más |

   - Las reglas se prueban con la visión reemplazada (caras, puntajes, tamaños, nitidez y huellas armadas) y con PostgreSQL real.
   - Las pruebas con caras reales leen `datos/prueba/` y se saltan, diciendo por qué, si la carpeta no existe. En la CI siempre se saltan: el repositorio no tiene caras.
6. Mide en el portátil cuánto tarda la respuesta a un recorte (RF-04 · C5 y RNF-03 · C1, meta de 1 s) y anótalo en la bitácora.
7. `servidor/README.md`: modelos, rutas y marcas nuevas.

## No hacer

- Nada de MQTT: ni el evento, ni la repetición publicada, ni la alerta (Día 3).
- No crees la asistencia (R5) ni las alertas (R6): son del Día 3. Los desconocidos sí guardan su evento.
- No guardes imágenes ni recortes: ni en disco, ni en la base, ni en los registros, ni para depurar.
- No subas los ONNX ni fotos de caras.
- No cambies los contratos. Si algo no encaja, propónlo en el PR.
- No calibres `UMBRAL_SIMILITUD` ni `NITIDEZ_MIN`: es del Día 4 (RNF-07).
- El modo extraer (RF-10 · C4) es del Día 4.

## Criterios de aceptación

- C1 (RF-04 · C1 a C4) La huella sale de YuNet + SFace con 128 números normalizados, se compara con pgvector, se aplican R1, R3 y R4, y la imagen solo vive en memoria.
- C2 (RF-02 · C4; RF-03 · C1 a C5; R9) La inscripción se abre, avanza, se completa, vence y se cancela por la API, con una sola activa por cámara.
- C3 (R7) Los 15 casos pasan, en el orden de la regla.
- C4 (`api-dispositivo.md`) Cada resultado y cada error del contrato tiene su prueba.
- C5 (RF-05 · C1 y C2) Los eventos se guardan como dice el contrato.
- C6 (RNF-01 · C1 y C3) No se guardan imágenes y nunca se dice a quién se parece una cara.
- C7 (RNF-04 · C1) La imagen de Docker construye para amd64 y arm64, con los modelos y su hash comprobado.
- C8 (RNF-06 · C3) `uv run pytest` en verde en el equipo (con las pruebas de caras reales, si tienes `datos/prueba/`) y en `servidor.yml`.
- C9 `servidor/README.md`, las specs y la bitácora al día, con el tiempo de respuesta medido.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado por marca (incluidas las de caras reales, si corrieron), qué decidiste (mensajes, cámara inactiva al abrir, orden de las comprobaciones y ruta de los modelos) y el tiempo medido.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA, con el commit de opencv_zoo y los dos SHA-256.
- Si cambiaste `arquitectura.md` o `.env.example`, sube su versión y su fecha.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con `servidor.yml` en verde. Cuando esté en `main`, avisa a A y a C para probar contra el servidor real y preparar el Hito 1.
- El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
