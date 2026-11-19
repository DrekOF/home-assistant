<!--
Nombre: README.md
Descripción: Servidor de AccesIA: API, reconocimiento, reglas, MQTT, MCP y la web compilada (frente B).
Fecha de creación: 2026-11-11
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 1.10
-->

# Servidor · frente B

Python 3.13 con FastAPI: saca la huella de la cara (YuNet + SFace), aplica las reglas, guarda en PostgreSQL con pgvector, publica en MQTT, sirve la web y, con otro comando, el servidor MCP del agente.

- Specs: `specs/arquitectura.md`, `specs/reglas.md`, `specs/modelo-datos.md` y todos los contratos.
- Lo crea la tarea `tareas/dia-1/B-cristhian-compose-y-base.md`. La tarea B1 del Día 2 suma la sesión y la API de administración; B2, el reconocimiento y la inscripción. Del Día 3, B1 suma la asistencia (R5) y la API de consulta, B2 el servidor en MQTT, y B3 el servidor MCP del agente y su semilla. Del Día 4, B1 sirve la web compilada y B2 suma el modo extraer de las cámaras de respaldo.

## Qué hay

| Ruta | Qué es |
| --- | --- |
| `accesia/config.py`, `db.py`, `tiempo.py` | Variables de `arquitectura.md`; motor de la base y una transacción por petición; hora de Colombia (R8) |
| `accesia/errores.py` y `esquemas.py` | El esquema `Error` y los esquemas de `openapi.yaml` 1.4 con pydantic |
| `accesia/sesion.py` y `seguridad.py` | Cookie de sesión firmada, primer administrador, Argon2id para las claves y SHA-256 para los tokens |
| `accesia/consentimiento.py` y `camaras.py` | Texto del consentimiento y la lógica de las cámaras que comparten la API y el comando |
| `accesia/modelos.py` y `vision.py` | YuNet y SFace fijos con su SHA-256, su nombre corto y su descarga; la visión solo en memoria: decodificar, detectar, recortar con la fórmula del contrato, huella y nitidez |
| `accesia/rostros.py`, `reconocimiento.py` e `inscripciones.py` | Lo que llega de la cámara (`enviarRostro`): comprobaciones en orden, 429 en memoria y el modo; R1 a R5 y R7 al reconocer, y lo que el recorte publica en MQTT; inscripciones (R9) y los seis pasos de R7 |
| `accesia/mqtt.py`, `descubrimiento.py`, `resumen.py` y `alertas.py` | El servidor en MQTT (`mqtt.md` 1.3): la conexión con último deseo; el Evento, la Alerta de R6, el Resumen y el descubrimiento con su limpieza; la disponibilidad y el estado de las cámaras |
| `accesia/asistencia.py` | R5 y R8: califica una llegada con el bloque del día (función pura) y registra la primera del día. La usan la cámara, el registro manual y la semilla del agente |
| `accesia/mensajes.py` y `registro.py` | Las frases del campo `mensaje`; los avisos INFO en el registro, con la hora de Colombia |
| `accesia/api/` | Rutas: `salud`, `sesion`, `personas`, `consentimiento`, `horarios`, `camaras`, `rostros`, `inscripciones`, `huellas`, `accesos`, `asistencia` y `configuracion` |
| `accesia/agente.py` | Las seis herramientas del agente (`mcp-agente.md`): las cinco consultas sobre las tres vistas del agente, cada una en una transacción `READ ONLY` de 3 s, y la de fecha y hora, que no toca la base. Devuelven lo del contrato o `{"error": …}` |
| `accesia/servidor_mcp.py` | El servidor MCP «AccesIA» con el SDK `mcp` 2.x (`MCPServer`): Streamable HTTP en `/mcp`, puerto 8001, sin sesiones y con el encabezado `Host` validado |
| `accesia/semilla.py` | `semilla agente`: los datos de la evaluación del agente, la revisión de las preguntas 1 a 9 y cómo convive con datos reales |
| `accesia/comandos.py` | El comando `accesia`: `crear-camara`, que también publica el descubrimiento de la cámara, `descargar-modelos`, `mcp` y `semilla agente` |
| `accesia/main.py` | La aplicación: al arrancar exige `SESION_SECRETO`, crea el primer administrador, carga los modelos de cara y se conecta a MQTT sin esperar al broker; cada 5 minutos publica el resumen. Si está compilada, sirve la web, y deja corriendo el modo extraer |
| `accesia/extraer.py` | El modo extraer de las cámaras de respaldo (RF-10 · C4): una tarea por cámara que pide su foto cada segundo, recorta la cara como la cámara y la procesa como `enviarRostro` |
| `accesia/web.py` | La web compilada (`web/dist`) en la raíz (D-04): un middleware que deja responder primero a la API y solo cambia por la web los 404 de `GET` y `HEAD` fuera de `/api` |
| `migraciones/` | Alembic. La migración `0001` ejecuta tal cual `specs/contratos/base-de-datos.sql` y crea el usuario `agente` |
| `pruebas/` | pytest con PostgreSQL 18 + pgvector y Mosquitto en contenedores (testcontainers); `armar.py` arma datos en la base, `vision_falsa.py` arma caras y huellas sin fotos, `mqtt_de_prueba.py` levanta Mosquitto y escucha como Home Assistant, y `hora_fija.py` fija la hora de las pruebas del agente |
| `Dockerfile` | Imagen multietapa con uv; se construye desde la raíz del repositorio, copia el SQL del contrato y `specs/consentimiento.md`, descarga los modelos de cara comprobando su SHA-256 y compila la web sin el simulacro |
| `pyproject.toml` y `uv.lock` | Dependencias, fijadas por uv |

## Requisitos

- uv: `winget install --id astral-sh.uv -e`. Después cierra y abre la terminal para que encuentre `uv`.
- Docker Desktop abierto: las pruebas levantan sus propios contenedores. Si dicen que no encuentran Docker (`CreateFile`), Docker Desktop está cerrado.

## Comandos

Desde la carpeta `servidor/`:

| Para qué | Comando |
| --- | --- |
| Instalar las dependencias, con las de pruebas | `uv sync` |
| Descargar YuNet y SFace a `datos/modelos/` y comprobar su SHA-256 (una vez; las pruebas también lo hacen si faltan) | `uv run accesia descargar-modelos` |
| Correr todas las pruebas | `uv run pytest` |
| Correr solo las de la ACL de MQTT | `uv run pytest -k acl` |
| Correr solo las del modo extraer | `uv run pytest pruebas/test_extraer.py` |
| Correr solo las del servidor en MQTT | `uv run pytest pruebas/test_mqtt.py pruebas/test_alertas.py pruebas/test_descubrimiento.py` |
| Correr solo las del agente: herramientas, semilla y servidor MCP | `uv run pytest -k "agente or semilla or mcp or lectura"` |
| Correr la API en el PC, contra la base de Compose | `$env:DATABASE_URL = "postgresql+psycopg://accesia:<clave>@127.0.0.1:5434/accesia"` y `$env:SESION_SECRETO = "<de infra/.env>"`, y luego `uv run uvicorn accesia.main:app --reload` |
| Aplicar las migraciones a mano | con `DATABASE_URL` y `AGENTE_DB_PASSWORD` en el entorno, `uv run alembic upgrade head` |
| Registrar una cámara en el PC | con `DATABASE_URL` en el entorno, `uv run accesia crear-camara entrada --nombre Entrada --tipo simulador` |
| Crear o borrar la semilla del agente en el PC | con `DATABASE_URL` del dueño de la base, `uv run accesia semilla agente` (o `--borrar`) |
| Correr el servidor MCP en el PC, contra la base de Compose | `$env:DATABASE_URL = "postgresql+psycopg://agente:<AGENTE_DB_PASSWORD>@127.0.0.1:5434/accesia"` y luego `uv run accesia mcp`; escucha en el 8001 |

La clave de PostgreSQL es `POSTGRES_PASSWORD` de `infra/.env`. En el contenedor no hace falta nada de esto: al arrancar aplica las migraciones y luego inicia Uvicorn con un solo proceso.

## Comando `crear-camara`

Registra una cámara sin pasar por la web (RF-10 · C5) y muestra su token una sola vez; la base guarda solo su SHA-256. Valida igual que `POST /api/v1/dispositivos`. Con Compose arriba, desde la raíz del repositorio:

```powershell
docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador
```

- `--tipo` es `tinyml`, `respaldo` o `simulador`; el tipo `respaldo` pide `--url-captura`.
- El código `servidor` está reservado. Si el código ya existe, no cambia nada y lo dice: el token se cambia desde la web o con `POST /api/v1/dispositivos/{codigo}/token`.
- Con `MQTT_URL`, que en el contenedor ya está, publica el descubrimiento de la cámara para Home Assistant (RF-07 · C1). Usa una conexión corta con client id vacío: el broker le asigna uno y no saca al servidor. Si el broker no responde, la cámara se crea igual, lo avisa, y el servidor publica el descubrimiento al reconectarse.
- La última línea que imprime es solo el token, para copiarlo sin errores.

## Sesión y primer administrador

- `POST /api/v1/sesion` deja la cookie `accesia_sesion`: firmada con `SESION_SECRETO`, `HttpOnly`, `SameSite=Strict` y `Path=/`. Solo guarda el id del administrador.
- La sesión dura 8 horas desde el último uso: cada respuesta con sesión renueva la cookie. Si el administrador se desactiva, su sesión deja de servir en la siguiente petición.
- Al arrancar, si no existe un administrador con `ADMIN_CORREO`, el servidor lo crea con `ADMIN_CLAVE_INICIAL` y el nombre «Administrador». Si ya existe, no toca su clave. Sin `SESION_SECRETO`, el servidor no arranca.
- Las claves se guardan con Argon2id. Un correo que no existe, una clave equivocada o un administrador inactivo responden lo mismo: 401 `credenciales_invalidas`.

## Modelos de cara

YuNet (`face_detection_yunet_2023mar.onnx`) y SFace (`face_recognition_sface_2021dec.onnx`) salen del commit `48b10fa` de `opencv/opencv_zoo`, con el tamaño y el SHA-256 que anota `specs/arquitectura.md` (Piezas). YuNet es el mismo archivo del simulador. OpenCV es `opencv-python-headless` 4.14.0.94, la misma versión del simulador sin ventanas.

- Van en `datos/modelos/` desde la raíz del repositorio, que Git y Docker ignoran. En la imagen quedan en `/app/datos/modelos`.
- `uv run accesia descargar-modelos` los baja y comprueba su tamaño y su SHA-256; lo que ya está y coincide no se vuelve a bajar. Las pruebas que usan los modelos reales lo hacen solas si faltan.
- La imagen los baja al construir, en una etapa que se reutiliza mientras `accesia/modelos.py` no cambie. Si el tamaño o el hash no coinciden, la construcción falla.
- Se cargan una vez, al arrancar. Sin ellos, el servidor no arranca y lo dice en el registro.
- Sus nombres cortos, `yunet_2023mar` y `sface_2021dec`, son los que muestra `GET /api/v1/configuracion`. El de SFace es también el valor por defecto de `rostro.modelo` en el SQL del contrato, y una prueba lo comprueba.

## La web

El servidor sirve la web de administración compilada en la raíz, en el mismo puerto 8000 (D-04). Con el Compose arriba, `http://localhost:8000` abre la web, sin Node.

- **En la imagen.**
  - La etapa `web` del `Dockerfile` compila la web con Node 24, como `web.yml`.
  - Corre una sola vez, en la plataforma que construye, porque el HTML, el JS y el CSS no dependen de la arquitectura.
  - Compila con `VITE_SIMULACRO=0`, borra `mockServiceWorker.js` y falla si algo del simulacro quedó en el paquete.
  - `dist` queda en `/app/web/dist`, de solo lectura.
- **En el PC.** El servidor busca `web/dist` desde la raíz del repositorio, como los modelos.
  - Si corriste `npm run build` en `web/`, `uv run uvicorn accesia.main:app` también la sirve.
  - Si no, arranca igual, lo dice en el registro y sirve solo la API.
  - Para trabajar en las pantallas sigue `npm run dev`.
- **Cómo responde** (`accesia/web.py`):
  - Primero responde la API. Solo un `GET` o un `HEAD` fuera de `/api` que termina en 404 se cambia por la web.
  - Si es un archivo de `dist`, sale ese archivo; si no, `index.html`, porque la web usa rutas del navegador. Así, recargar `/personas` funciona.
  - Un archivo que falta en `assets/` da 404, y una ruta con `..` nunca sale de `dist`.
  - `/api` responde igual que sin la web: una ruta que no existe es 404 `no_encontrado` y un método que no acepta es 405 con `Allow`. Un `POST` a una ruta de la web también es 404.
  - Es un middleware y no una ruta comodín para que las rutas de la API, también las que se agreguen después, respondan primero.
- **Caché.**
  - Los archivos de `assets/` llevan hash y salen con `Cache-Control: public, max-age=31536000, immutable`.
  - `index.html` y lo demás salen con `no-cache`, para que una web nueva se vea al recargar.
  - Todos llevan `X-Content-Type-Options: nosniff`.

## Reconocimiento e inscripción

`POST /api/v1/dispositivos/{codigo}/rostros` (`enviarRostro`) no usa la sesión: la cámara se identifica con su token Bearer, que se compara por su SHA-256 con `hmac.compare_digest`. Las comprobaciones van en este orden y se responde la primera que falla:

| Orden | Respuesta | Cuándo |
| --- | --- | --- |
| 1 | 401 `token_invalido` | Falta el token, no corresponde o la cámara no existe; no se dice cuál de las tres |
| 2 | 403 `dispositivo_inactivo` | La cámara está desactivada |
| 3 | 415 `tipo_no_soportado` | El `Content-Type` no es `image/jpeg` (se aceptan parámetros y mayúsculas) |
| 4 | 422 `validacion` | `X-AccesIA-Imagen` no es `recorte` ni `cuadro` (contrato cámara 1.3) |
| 5 | 413 `imagen_grande` | El cuerpo pasa de 100 KB, es decir de 102 400 bytes (contrato cámara 1.2); se corta sin leerlo entero |
| 6 | 429 `demasiadas_peticiones` | Llegaron dos recortes de esa cámara con menos de 0,8 s; lleva `Retry-After: 1`. Cuenta desde el último recorte aceptado: un 429 no mueve el reloj |
| 7 | 422 `imagen_invalida` | El cuerpo no es un JPEG que se pueda leer |

- Desde el paso 2, toda petición guarda `ultimo_contacto`, aunque falle después.
- La imagen solo vive en memoria: no se escribe en disco ni aparece en el registro (RNF-01).
- Antes de decidir el modo, la inscripción de la cámara vence si ya pasó su hora (R9). Con una inscripción activa, la cámara inscribe (los seis pasos de R7); si no, reconoce (R1 a R4).
- R1 compara con el umbral con una tolerancia de 1e-6, porque pgvector calcula en float32 (`specs/reglas.md`).
- Una repetición de R4 devuelve el resultado, el motivo, la persona y el `evento_id` del evento original, con la similitud del recorte nuevo, y no guarda nada.
- **El cuadro completo** (contrato cámara 1.3, por D-24 si P-05 elige el modelo de personas):
  - con `X-AccesIA-Imagen: cuadro`, el servidor hace lo que haría la cámara: YuNet en el cuadro, la cara más grande, `CARA_MIN_PX` sin el 0,8 y la fórmula del recorte (`recortar_cara_mas_grande`). El recorte sigue el camino de siempre;
  - sin cara, o con una cara más pequeña que `CARA_MIN_PX`, responde `sin_cara` o `cara_pequena`, como con un recorte;
  - la línea INFO de ese recorte dice `cuadro`.
- `accesia/vision.py` tiene `recortar_cara_mas_grande`: detecta con YuNet en un cuadro completo, elige la cara de mayor área y recorta con la fórmula del contrato, y con `CARA_MIN_PX` descarta las caras más pequeñas, como la cámara. La usa el modo extraer (RF-10 · C4) y la usaría una cámara que envíe cuadros completos.

Mensajes (`mensaje`): no dependen del género y nunca nombran a quien se parece una cara (RNF-01 · C3).

| Resultado | Mensaje |
| --- | --- |
| `permitido` | «Hola, Ana. Puedes pasar» (el primer nombre) |
| `denegado` | «Acceso denegado: persona inactiva» o «Acceso denegado: falta el consentimiento» |
| `desconocido` | «No te reconozco» |
| `descartado` | «No veo una cara» o «Acércate a la cámara» |
| `muestra_aceptada` | «Muestra 3 de 5»; con la última, «Muestra 5 de 5: inscripción completa» |
| `muestra_rechazada` | `sin_cara` «No veo una cara», `varias_caras` «Que se vea una sola cara», `cara_pequena` «Acércate a la cámara», `borrosa` «Imagen borrosa: no te muevas», `parece_otra_persona` «Se parece a otra persona inscrita», `distinta_de_la_primera` «No se parece a la primera muestra» |

Inscripciones (con sesión):

- `POST /api/v1/inscripciones` responde 404 si la persona o la cámara no existen, y 422 `validacion` si la cámara está desactivada (R9 pide una cámara activa y el contrato no tiene otro código). Sin consentimiento vigente responde 422 `sin_consentimiento`. Después vence la activa de esa cámara si ya pasó su hora, y si sigue habiendo una, 409 `inscripcion_activa`.
- `requeridas` es `INSCRIPCION_MUESTRAS`, y `vence` es la hora de apertura más `INSCRIPCION_VENCE_S`.
- `GET` y `DELETE /api/v1/inscripciones/{inscripcion_id}` primero la vencen si ya pasó su hora. Cancelar una que ya terminó responde 409 `inscripcion_terminada`.

## Modo extraer (cámaras de respaldo)

Una cámara de tipo `respaldo` no necesita firmware de AccesIA: basta con que entregue una foto JPEG por HTTP. El servidor le pide un cuadro cada segundo, recorta la cara más grande como lo haría la cámara y la procesa por el mismo camino de `enviarRostro` (RF-10 · C4; `api-dispositivo.md`, «Modo extraer»). Sirve para un ESP32-CAM sin tocar su firmware y para un celular con una aplicación de cámara IP.

### Registrar una cámara de respaldo, paso a paso

1. **Conecta la cámara al hotspot** (`AccesIA`, 2,4 GHz) y anota su IP.
   - ESP32-CAM con el ejemplo `CameraWebServer` de Arduino: la IP sale en su monitor serial al arrancar.
   - Celular: la IP la muestra la aplicación de cámara IP.
2. **Busca la URL que entrega una sola foto JPEG** y ábrela en el navegador del portátil. Debe mostrar una foto, no una página ni un video.
   - ESP32-CAM con `CameraWebServer`: `http://<IP>/capture`. La de `:81/stream` es un video y no sirve.
   - Celular: la URL de «foto» o «snapshot» de la aplicación; por ejemplo, en IP Webcam (Android), `http://<IP>:8080/shot.jpg`.
   - Mejor una resolución baja: VGA (640 × 480) o SVGA (800 × 600) alcanza para una cara a 1 o 2 m, y el servidor la procesa más rápido.
3. **Registra la cámara con esa URL.** En la web: Cámaras → Nueva cámara, con el tipo «Respaldo» y la URL de captura. O con el comando, desde la raíz del repositorio y con el Compose arriba:

   ```powershell
   docker compose -f infra/compose.yaml exec servidor accesia crear-camara patio --nombre Patio --tipo respaldo --url-captura http://192.168.137.60/capture
   ```

   El comando muestra un token; esta cámara no lo necesita.
4. **Comprueba que el servidor la está pidiendo.** Empieza en menos de 5 s, sin reiniciar:
   - el registro del servidor (`docker compose -f infra/compose.yaml logs -f servidor`) dice `Cámara patio: modo extraer, pide http://192.168.137.60/capture cada segundo.`;
   - en la web, la cámara aparece en línea.
   - Si la URL falla, el registro lo dice una vez, con el motivo (por ejemplo, `la URL de captura no respondió en 3 s`), y otra vez cuando vuelve a capturar.
5. **Inscribe a alguien** con esa cámara, desde la pantalla Inscripción, como con cualquier otra: la cámara de respaldo también inscribe (R7 y R9).
6. **Prueba el reconocimiento** frente a la cámara. El registro muestra una línea por recorte, con `firmware modo-extraer`, y Home Assistant recibe el evento.
7. **Para dejar de usarla, desactívala en la web:** el servidor deja de pedirle fotos antes de la captura siguiente. Si le cambias la URL, usa la nueva sin reiniciar.

- El servidor tiene que alcanzar la cámara. Con D-22, el servidor corre en la Pi, así que la cámara va en el hotspot. En el portátil (plan B), el contenedor del servidor también alcanza las IP del hotspot.
- Para probar sin cámara, con el Compose del portátil: una foto en una carpeta de `datos/` (Git la ignora, y la foto va con el permiso de quien aparece), servida con `python -m http.server 8099` desde esa carpeta, y la URL `http://host.docker.internal:8099/foto.jpg`.

### Qué decidió B2 del Día 4

El contrato no cambia: todo cabe en «Modo extraer» de `api-dispositivo.md` y en las esperas que el contrato fija para la cámara.

- **El ritmo**, como la cámara del contrato: 1 s desde que termina un cuadro, y 3 s después de `permitido`, `denegado` o `desconocido`.
- **La captura:**
  - `GET` con 3 s de espera para todo el pedido;
  - solo `http` y `https`, y sin seguir redirecciones (una 3xx pide poner la URL final);
  - tope de 2 MB por cuadro. Los 100 KB del contrato son para recortes: un cuadro de un ESP32-CAM pesa de 10 a 250 KB y una foto 1080p de un celular, menos de 1 MB. Lo que pasa de 2 MB suele ser un video.
- **El recorte**, como la cámara: la cara más grande con puntaje de 0,9 o más, y solo si mide al menos `CARA_MIN_PX`, con la fórmula del contrato y en JPEG de calidad 80. Después, `rostros.procesar`, el mismo código de `enviarRostro`.
- **Sin cara** no se procesa nada: no hay evento (RF-05 · C2) ni línea en el registro.
- **El último contacto** cambia con cada captura buena, haya cara o no. De ahí sale `en_linea`, porque la cámara no tiene MQTT.
- **Los errores:**
  - cuáles: no responde en 3 s, no se pudo conectar, una respuesta que no es 200, más de 2 MB o algo que no es un JPEG;
  - se reintentan con espera de 1, 2, 4, 8 y hasta 10 s, como la cámara con un 5xx;
  - el registro avisa una vez por motivo y otra cuando vuelve a capturar, sin una línea por segundo. La URL va sin usuario, clave ni parámetros.
- **MQTT:** el evento, la alerta y el resumen se publican después de confirmar la transacción y solo con conexión, como en `enviarRostro`.
- **Una tarea por cámara**, en paralelo, así que una lenta no frena a las demás. Un supervisor busca cada 5 s las cámaras nuevas o reactivadas, y cada tarea revisa su cámara antes de cada captura.
- **Nada en disco:** el cuadro y el recorte solo viven en memoria (RNF-01 · C1).

## Asistencia

R5 vive en `accesia/asistencia.py`:

- `calificar_llegada(llegada, bloque)` es una función pura. El bloque es el del horario de la persona para el día de la semana de la fecha local (1 = lunes … 7 = domingo); sin horario, o sin bloque ese día, la llegada es `sin_horario`. Es `a_tiempo` hasta el inicio del bloque más su tolerancia, con ese segundo incluido; después es `tarde`, con los minutos completos desde el inicio.
- `registrar_llegada(…)` hace `INSERT … ON CONFLICT (persona_id, fecha) DO NOTHING` y devuelve la llegada creada, o nada si ya había una ese día: cuenta la primera, venga de la cámara o sea manual. Con dos registros a la vez, PostgreSQL hace esperar al segundo hasta que el primero termina, y el segundo no escribe; como no hay error, no hace falta un savepoint.
- La fecha es la fecha local de Colombia (R8) y la llegada se guarda sin microsegundos.

Desde la cámara:

- La primera entrada permitida del día crea la llegada en la misma transacción del evento, con origen `camara` y su `evento_id`.
- No la crean las repeticiones de R4 (tampoco una repetición pasada la medianoche), los denegados, los desconocidos ni las muestras de una inscripción.
- `reconocer` devuelve además la llegada que creó, para que B2 la publique en el campo `asistencia` del Evento (`mqtt.md`). La respuesta a la cámara no cambia.

Con sesión:

- `POST /api/v1/asistencia` (`registrarAsistenciaManual`) aplica R5 a la hora dada, que puede venir en cualquier zona, y guarda al administrador de la sesión en `registrado_por`.
  - Responde 404 si la persona no existe, 422 `validacion` si la hora es futura o no trae zona, y 409 `asistencia_duplicada` si ya tiene llegada ese día.
  - También sirve para una persona inactiva: R5 no lo impide.
- `GET /api/v1/asistencia` (`verAsistencia`) da el reporte de la fecha pedida, o de hoy en Colombia si no se pide.
  - Las listas van por hora de llegada, y los ausentes por nombre, con la colación española.
  - Los ausentes se calculan con el horario y el estado que la persona tiene hoy, porque la base no guarda su historia.
- `GET /api/v1/personas/{persona_id}/asistencia` (`verAsistenciaPersona`) da las llegadas de la más reciente a la más antigua.
  - Sin fechas, todas; con una sola, el rango queda abierto por el otro lado.
  - Con `desde` posterior a `hasta`, 422.
- `GET /api/v1/asistencia.csv` (`exportarAsistencia`, el extra RF-06 · C4) da las llegadas del rango por fecha y hora de llegada.
  - Lleva las columnas del contrato, con coma y UTF-8, y el nombre `asistencia-<desde>-a-<hasta>.csv`.
  - Un nombre o un documento que empieza con `=`, `+`, `-` o `@` sale con un `'` delante, para que Excel o LibreOffice no lo ejecuten como fórmula.

## MQTT

El servidor cumple `specs/contratos/mqtt.md` 1.3 con `paho-mqtt` 2.2 (`accesia/mqtt.py`). Se conecta con `MQTT_URL`, que arma Compose con el usuario `servidor`.

Conexión:

- El client id es `servidor`, un código reservado: ninguna cámara puede usarlo y sacar al servidor del broker.
- El último deseo es `offline`, retenido, en `accesia/servidor/disponible`. Al conectarse publica `online`, y al apagarse en orden publica `offline`.
- Arranca sin esperar al broker: si no responde, el servidor sigue y paho reintenta solo, entre 1 y 30 s. Mientras tanto, la salud dice `mqtt: sin_conexion` y `estado: degradado`.
- En cada conexión, también al arrancar, publica el descubrimiento del servidor y de todas las cámaras, revisa la limpieza y publica el resumen. Lo que necesita la base lo hace en un hilo aparte, para no frenar el de paho.
- **Solo publica con conexión.** Sin ella, descarta el mensaje y lo anota en el registro. paho 2.2 guardaría un mensaje QoS 1 y lo mandaría al reconectar, y un `permitido` viejo abriría la puerta minutos después. Lo retenido se vuelve a publicar al reconectar.
- Queda un caso raro: si la conexión se corta justo después de publicar y antes de que el broker confirme, paho reenvía ese mensaje al reconectar.

Qué publica y cuándo:

| Tema | Cuándo |
| --- | --- |
| `accesia/{codigo}/evento` | Después de confirmar la transacción de cada evento guardado. También en la repetición de un `permitido`, con `repetido: true`; nunca en la de un `denegado` (R4). Una tarea de fondo de FastAPI lo publica apenas sale la respuesta a la cámara: si algo falla antes de confirmar, no se publica nada |
| `accesia/{codigo}/alerta` | Con R6, en la misma tarea, después del evento. La hora de la última alerta de cada cámara vive en memoria |
| `accesia/resumen` | Al conectarse, después de cada evento guardado, después de cada llegada manual y cada 5 minutos, así cambia de día a medianoche. `ultima_llegada` es la de hora más reciente del día, y `null` si nadie ha llegado |
| `homeassistant/…/config` | Al conectarse y cuando Home Assistant publica `online` en `homeassistant/status`. Los de una cámara, también después de crearla o editarla por la API, o con `crear-camara` |

Descubrimiento (decisiones de B2 del Día 3):

- El `model` es «XIAO ESP32-C6» en todas las cámaras, también en las de tipo `simulador`. En la demo, `entrada` se crea como `simulador` porque envía los recortes, pero su dispositivo en Home Assistant es la placa, con su puerta y sus sensores.
- `device.identifiers` y el nodo del tema llevan el código tal cual (`accesia_entrada-2`), y `unique_id` y `default_entity_id` lo llevan con guion bajo, igual que los config de la placa. Así Home Assistant junta en un solo dispositivo las entidades del servidor y los sensores de la placa.
- `sw_version` y `origin` llevan la versión del servidor.
- Los tres sensores del resumen dependen de la disponibilidad del servidor. «Servidor en línea» y «Cámara en línea» no tienen disponibilidad, como dice el contrato.
- El icono y `json_attributes_topic` van solo en «Última persona», como en el ejemplo del contrato.

Limpieza del descubrimiento (`mqtt.md` 1.3):

- El servidor se suscribe a `homeassistant/+/+/+/config` y mira solo los retenidos que el broker le entrega al suscribirse. Así revisa todo en cada conexión.
- Son suyos los de nodo `accesia_{codigo}`. Si esa cámara ya no está en la base, publica un mensaje vacío retenido, y Home Assistant deja de mostrar su dispositivo.
- Nunca toca los de la placa (nodo `{codigo}`), aunque su cámara ya no exista: esos se borran a mano.
- Pasa si la base empieza de cero y el broker conserva lo retenido, porque su volumen es aparte, o si se borra una cámara a mano. La API no borra cámaras.

Cámaras:

- El servidor escucha `accesia/+/disponible` y `accesia/+/estado`, que son retenidos, así que los recupera en cada conexión. Los guarda en memoria por código.
- `en_linea` es verdadero con `online` en MQTT, mientras el servidor siga conectado al broker, o con un contacto por HTTP en los últimos 2 minutos.
- `estado` es el último EstadoCamara válido y se conserva aunque se pierda el broker. Descarta, con un aviso en el registro, lo que no es un objeto JSON o no cumple sus tipos; un `null` tampoco cumple. La API devuelve solo los campos que mandó la cámara (`openapi.yaml` 1.4).

Para mirar el tráfico con el Compose arriba, desde la raíz:

```powershell
docker compose -f infra/compose.yaml exec mosquitto mosquitto_sub -u servidor -P "<MQTT_SERVIDOR_CLAVE de infra/.env>" -t "accesia/#" -t "homeassistant/#" -v
```

## Servidor MCP del agente

`accesia mcp` arranca el servidor MCP «AccesIA» de `specs/contratos/mcp-agente.md` 1.5. En Compose lo corre el servicio `mcp`, con la misma imagen del servidor.

- **SDK y transporte.**
  - Usa el SDK oficial `mcp` 2.x, donde FastMCP se llama `MCPServer`.
  - Sirve Streamable HTTP en `http://0.0.0.0:8001/mcp`, sin sesiones y con respuestas JSON: cada pedido es independiente, así que si el contenedor se reinicia, Home Assistant no queda con una sesión vieja.
  - No pide autenticación (D-16).
- **Solo lectura, en tres capas (D-15).**
  - Solo arranca si `DATABASE_URL` usa el usuario `agente`, que solo lee las tres vistas del agente. Con otro usuario sale con un error.
  - Cada herramienta corre en su propia transacción `READ ONLY`, con `statement_timeout` de 3 s.
  - Las cinco consultas solo leen, y `fecha_y_hora_GetDateTime` no toca la base. Las seis se anuncian con `readOnlyHint`.
- **Encabezado `Host`.** El SDK lo valida contra DNS rebinding.
  - Acepta `mcp:8001`, `localhost:8001`, `127.0.0.1:8001` y los de `MCP_HOSTS_PERMITIDOS`, separados por comas (por defecto, `192.168.137.1:8001`, la IP del portátil en el hotspot).
  - Otro `Host` recibe 421, y un pedido con encabezado `Origin` (un navegador), 403.
  - Al arrancar, el registro dice qué `Host` acepta: `docker compose -f infra/compose.yaml logs mcp`.
- **Respuestas.**
  - Un error de regla (fecha mal escrita, más de 31 días, horas fuera de 1 a 168, nombre de menos de 2 caracteres) o de la base vuelve como `{"error": "…"}` en español, nunca como excepción.
  - Un tipo que no se puede convertir, como `horas = "mucho"`, lo rechaza el SDK antes de llegar a la herramienta, como un resultado de error de MCP.
  - Lo que el contrato no decía quedó en `mcp-agente.md` 1.3:
    - con más de 50 accesos van los 50 más recientes, en orden de hora, y `total` cuenta todos;
    - `ultimos` lleva las 10 horas más recientes, de la más antigua a la más nueva;
    - una persona sin horario tiene `"horario": null`.
  - Las palabras `hoy`, `ayer` y `antier` se aceptan sin importar mayúsculas.
  - Las listas van por hora, y los ausentes y las coincidencias por nombre.
- **`fecha_y_hora_GetDateTime` (`mcp-agente.md` 1.5).** Da la fecha, el día y la hora en Colombia. El sufijo en inglés hace que Home Assistant no agregue al prompt su línea de fecha y hora, que cambia cada segundo; así Ollama reutiliza de su caché las instrucciones y las herramientas entre preguntas (D-22).
- **La caché del prompt, medida.** `scripts/cache_del_prompt.py` arma cada pedido a Ollama como lo arma Home Assistant y muestra el `prompt_eval_count` de cada pregunta, antes (1.4) y después (1.5). Necesita Ollama con el modelo ya descargado:

  ```powershell
  docker run -d --name ollama-cache -p 127.0.0.1:11434:11434 -e OLLAMA_NUM_PARALLEL=1 -e OLLAMA_KEEP_ALIVE=-1 -e OLLAMA_KV_CACHE_TYPE=q8_0 -e OLLAMA_FLASH_ATTENTION=1 -v ollama-cache:/root/.ollama ollama/ollama:0.40.16
  docker exec ollama-cache ollama pull qwen2.5:1.5b
  uv run python scripts/cache_del_prompt.py --modelo qwen2.5:1.5b
  docker rm -f ollama-cache
  ```

  Usa las variables del complemento de Ollama de la Pi, con `OLLAMA_FLASH_ATTENTION=1`: con 0, Ollama 0.40.16 no carga el modelo. Se mide con Ollama recién arrancado, porque `llama-server` también guarda en RAM prompts de pedidos anteriores.

## Semilla del agente

`accesia semilla agente` crea los datos de la evaluación de `mcp-agente.md`:

- las seis personas, con los documentos `SEMILLA-01` a `SEMILLA-06`;
- el horario «Clase todos los días» y sus consentimientos;
- los 14 eventos de la tabla en la cámara `entrada`, con fechas relativas a hoy en hora de Colombia, y sus 8 llegadas calificadas con `registrar_llegada` (R5).

Con Compose arriba, desde la raíz del repositorio (con el servicio `servidor`, que usa el dueño de la base):

```powershell
docker compose -f infra/compose.yaml exec servidor accesia semilla agente
```

- **Con datos reales**, por ejemplo los del Hito 1:
  - Si la base tiene personas o eventos que no son de la semilla, no escribe nada y lo explica: las preguntas 2, 4 y 6 cuentan a todos, así que su respuesta puede cambiar.
  - Con `--con-datos-reales`, agrega sus datos junto a los reales. Nunca cambia ni borra lo que no creó.
- **La cámara `entrada`:** si existe, la usa sin tocarla. Si no, la crea como `simulador` y no muestra su token; si la vas a usar, cámbiale el token en la web.
- **Repetirla** reemplaza solo lo suyo, con las fechas de ese día: así se mide otro día sin borrar nada a mano.
- **`--borrar`** quita solo lo que creó: sus eventos, sus personas (con sus consentimientos y llegadas) y su horario, si nadie más lo usa. La cámara se queda.
- **Revisión.** Al terminar, responde las preguntas 1 a 9 con las mismas consultas de las herramientas y dice cuáles dan la respuesta del contrato. Por ejemplo, con una persona real que faltó ayer:

  ```text
  Preguntas 1 a 9 con las herramientas: 8 de 9 como dice el contrato.
    ✓ 1. ¿Quién llegó tarde ayer? Carla Ruiz, 12 minutos
    ✗ 2. ¿Quién faltó ayer? El contrato espera «Felipe Soto»; con los datos de ahora, asistencia_del_dia da «Felipe Soto, Rosa Real».
  ```

  Así, quien mide el agente (C2) sabe contra qué respuesta comparar.
- Lo suyo lo reconoce por identificadores fijos (uuid5 de un espacio propio): sus personas, su horario y sus eventos.

## Registro

Los avisos INFO del paquete `accesia` salen por la salida de errores, y así se ven en `docker compose -f infra/compose.yaml logs servidor`. Antes, uvicorn solo configuraba sus propios registros, y los de `accesia` solo salían desde WARNING. Cada recorte deja una línea, sin imagen y sin decir a quién se parece un desconocido:

```text
2026-11-12T16:43:06-05:00 INFO accesia.rostros: Cámara entrada · reconocer · permitido · similitud 0.712 · calidad 143.2 · persona 01a1… · llegada tarde 12 min · firmware simulador-1.0.0 · 12 ms
2026-11-12T16:43:08-05:00 INFO accesia.rostros: Cámara entrada · inscribir · muestra_rechazada (borrosa) · calidad 41.7 · persona 01a1… · inscripción 01a1… 2/5 activa · 11 ms
2026-11-12T16:43:09-05:00 INFO accesia.rostros: Cámara entrada: 429 demasiadas_peticiones.
```

- `calidad` es la nitidez de R7: sirve para recalibrar `NITIDEZ_MIN` en clase (D-14).
- `llegada` solo aparece cuando ese evento creó la llegada del día: `a_tiempo`, `tarde` con sus minutos, o `sin_horario`.
- Borrar huellas también deja una línea con cuántas y de qué persona (RF-12 · C1).
- MQTT deja una línea al conectarse (`MQTT: conectado a mosquitto:1883 como servidor.`), otra por cada alerta de R6 y por cada config que borra la limpieza. Avisa, una sola vez hasta reconectar, si no puede conectarse, y avisa también por cada mensaje que descarta sin conexión y por cada EstadoCamara que no cumple.

## Rutas

Todas piden sesión (401 `sin_sesion` sin ella), menos `GET /api/v1/salud`, `POST /api/v1/sesion` y `POST /api/v1/dispositivos/{codigo}/rostros`, que usa el token de la cámara. `DELETE /api/v1/sesion` responde 204 haya sesión o no. `GET /api/v1/salud` dice `mqtt: ok` si el servidor está conectado al broker, y `estado: ok` solo con la base y MQTT bien.

| Rutas | Operaciones de `openapi.yaml` |
| --- | --- |
| `/api/v1/sesion` | `iniciarSesion`, `verSesion`, `cerrarSesion` |
| `/api/v1/personas` y `/api/v1/personas/{persona_id}` | `listarPersonas`, `crearPersona`, `verPersona`, `editarPersona`, `borrarPersona` |
| `/api/v1/consentimiento/texto`, `/api/v1/personas/{persona_id}/consentimiento` y `…/consentimientos` | `verTextoConsentimiento`, `verConsentimiento`, `registrarConsentimiento`, `revocarConsentimiento`, `listarConsentimientos` |
| `/api/v1/horarios` y `/api/v1/horarios/{horario_id}` | `listarHorarios`, `crearHorario`, `editarHorario`, `borrarHorario` |
| `/api/v1/dispositivos`, `/api/v1/dispositivos/{codigo}` y `…/token` | `listarCamaras`, `crearCamara`, `verCamara`, `editarCamara`, `cambiarTokenCamara` |
| `/api/v1/dispositivos/{codigo}/rostros` | `enviarRostro` (token de la cámara) |
| `/api/v1/inscripciones` y `/api/v1/inscripciones/{inscripcion_id}` | `abrirInscripcion`, `verInscripcion`, `cancelarInscripcion` |
| `/api/v1/personas/{persona_id}/rostros` y `/api/v1/rostros/{rostro_id}` | `listarRostros`, `borrarRostros`, `borrarRostro` |
| `/api/v1/accesos` | `listarAccesos` |
| `/api/v1/asistencia`, `/api/v1/asistencia.csv` y `/api/v1/personas/{persona_id}/asistencia` | `verAsistencia`, `registrarAsistenciaManual`, `exportarAsistencia`, `verAsistenciaPersona` |
| `/api/v1/configuracion` | `verConfiguracion` |

Donde el contrato no dice nada, la API responde como el simulacro de la web: personas ordenadas por nombre con la colación española, un horario que no existe es 422 `validacion`, un `PATCH` vacío también, y un id que no es un uuid es 404. Una ruta que existe, llamada con otro método, responde 405 `metodo_no_permitido` (contrato 1.3).

Lo que decidió B1 del Día 3 donde el contrato no dice nada:

- **Accesos.**
  - Van del más reciente al más antiguo y, con la misma hora, el último guardado primero (los id son uuidv7).
  - `desde` y `hasta` entran en el rango y llevan zona: una hora sin zona no es un `date-time` del contrato y da 422.
  - Una persona o una cámara que no existe da una página vacía, no 404, y `total` cuenta con los mismos filtros.
- **Huellas.**
  - Las muestras se listan en el orden en que se guardaron, sin la huella.
  - Borrar las de una persona que no tiene ninguna responde 204.
- **Configuración.** Muestra los valores que el servidor leyó de `infra/.env` al arrancar (D-14).

## Pruebas

Cada prueba lleva su marca (`@pytest.mark.marca("…")`) y pytest no corre si alguna no la tiene. Al final, pytest muestra cuántas pasaron por marca.

Las pruebas de la API usan la conexión de la prueba, dentro de una transacción que se deshace al final. Cada petición corre en su savepoint, como una transacción del servidor real, y las consultas que pueden chocar con una restricción abren otro: así, después de un 409, la prueba sigue sin que PostgreSQL deje la transacción abortada.

Las pruebas de MQTT usan un Mosquitto con la configuración y la ACL del repositorio, para toda la sesión de pytest:

- La fixture `escucha` recibe todo como Home Assistant, con la QoS y la retención de cada mensaje. Al terminar borra lo retenido.
- `conectar_mqtt` conecta el cliente del servidor y espera a que llegue todo lo que publica al conectarse.
- Ese cliente usa la conexión de la prueba por turnos con las peticiones (`candado_de_la_base`), porque trabaja en sus propios hilos. La espera con tiempo límite: si una petición la tiene tomada, la prueba falla en vez de colgarse.
- Para afirmar que algo no se publicó, la prueba publica una marca por la conexión del servidor: si llegó la marca, ya llegó todo lo anterior.

Las reglas se prueban con la visión armada de `pruebas/vision_falsa.py` (caras con puntaje, tamaño, nitidez y huella elegidos, sin fotos) y PostgreSQL real. La fixture `reloj` controla `accesia.tiempo.ahora()` en todos los módulos, y cada cámara de prueba avanza 1 s el reloj del 429 en cada recorte. Las pruebas con caras reales leen las fotos `<persona>-<n>` de `datos/prueba/`, la carpeta del modo carpeta del simulador, sin las que `esperado.json` marca como no enviadas; sin fotos se saltan, y en la CI siempre se saltan.

| Marca | Qué comprueba |
| --- | --- |
| `contrato BD · esquema` | La base migrada tiene las mismas tablas, columnas, restricciones, índices, vistas y permisos que el contrato cargado aparte |
| `contrato BD · vector` | La búsqueda central de `modelo-datos.md` devuelve la muestra más parecida (R2) |
| `contrato BD · horarios` | Horarios por bloques (D-20): cinco bloques en «Clase IA», un bloque por día, borrado en cascada, `restrict_violation` (23001) al borrar uno en uso y días de la vista del agente |
| `RF-08 · C4` | El usuario `agente` lee sus tres vistas y no puede leer `persona`, `rostro` ni `horario_bloque`, ni cambiar las tablas. Cada herramienta corre en una transacción de solo lectura con 3 s de límite, y el servidor MCP no arranca con otro usuario |
| `contrato agente · <herramienta>` | Las seis herramientas con los datos de la semilla y el usuario `agente`: lo que devuelven, sus límites (10 personas, 31 días, 50 accesos, de 1 a 168 horas y 10 en `ultimos`) y sus errores como `{"error": …}` |
| `contrato agente · preguntas` | Las preguntas 1 a 9 de la evaluación, cada una con su herramienta esperada |
| `contrato agente · evaluación` | `semilla agente` crea la tabla de la evaluación con fechas relativas a hoy; con datos reales no escribe sin `--con-datos-reales` y nunca los toca; se repite y se borra sola |
| `contrato agente · host` | El servidor MCP acepta el `Host` de `mcp:8001`, `localhost:8001`, `127.0.0.1:8001` y `MCP_HOSTS_PERMITIDOS`; otro `Host` recibe 421 y un pedido con `Origin`, 403 |
| `RF-08 · C1` | Un cliente MCP real, por Streamable HTTP contra el servidor en uvicorn, lista las seis herramientas (en español y de solo lectura) y las llama |
| `contrato agente · home assistant` | Los esquemas de las seis herramientas se convierten con `probatio`, como en Home Assistant (si uno fallara, Assist se quedaría sin todas), y una sola termina en `GetDateTime` |
| `contrato agente · instrucciones` | Las instrucciones de `mcp-agente.md` no llevan plantillas y nombran `fecha_y_hora_GetDateTime`: son el mismo texto en cada pregunta |
| `RNF-01 · C4` | Ninguna respuesta de las herramientas trae documentos, huellas ni similitudes |
| `contrato API · salud` | `GET /api/v1/salud` cumple el esquema `Salud`, da la hora con `-05:00` y dice `mqtt: ok` solo con el broker conectado |
| `contrato API · error` | Validación, ruta inexistente, método no permitido (405 con `Allow`) y error interno responden con el esquema `Error`, también con la web encendida, y un `POST` a una ruta de la web es 404 |
| `D-04 · web servida` | La raíz y las rutas del navegador devuelven `index.html` con `no-cache`; `assets/` sale con su tipo y caché larga; un archivo que falta en `assets/` da 404; `HEAD` responde; ninguna ruta sale de `dist`; sin `dist`, la raíz da 404 y la API responde |
| `contrato API · <operationId>` | Cada operación de sesión, personas, consentimiento, horarios, cámaras, huellas, accesos, asistencia y configuración responde con su esquema y con los códigos de error del contrato |
| `contrato API · inscripcion_activa` | Una cámara muestra su inscripción activa y `modo: inscribir`; si ya pasó su hora, la vence y el campo queda en `null` (R9) |
| `RNF-02 · C2` | Cookie `HttpOnly`, `SameSite=Strict`, `Path=/` y de 8 horas; primer administrador con Argon2id; sin `SESION_SECRETO` no arranca |
| `RNF-02 · C5` | Cada ruta con sesión responde 401 `sin_sesion` sin cookie, con una firma falsa, con una cookie vencida o con el administrador desactivado |
| `RF-02 · C1`, `C2` y `C5` | Documento único, activar y desactivar; consentimiento con versión, medio, autor y fecha; revocar borra las huellas |
| `RF-10 · C1`, `C2`, `C3` y `C5` | Token mostrado una vez y guardado como SHA-256, cambio de token, en línea por MQTT o por el último contacto, el estado de MQTT (lo que no cumple se descarta) y el comando `crear-camara` |
| `RF-12 · C2` | Borrar una persona borra lo suyo y deja sus eventos sin persona |
| `RF-13 · C1`, `C2` y `C3` | Horarios por bloques, reemplazo de bloques y `horario_en_uso` |
| `R8 · formato` | Las fechas de la API salen en ISO 8601 con `-05:00` |
| `R9 · revoca a mitad` y `R9 · desactivar no cancela` | Revocar cancela la inscripción activa y borra sus huellas, y la siguiente cara se reconoce; desactivar a la persona no la cancela |
| `R1 · <caso>`, `R2 · <caso>` y `R3 · <caso>` | Umbral (también 0,363 menos un paso de float32), la muestra más parecida y el estado de la persona, con `revocado de punta a punta` por la API |
| `R4 · <caso>` | Ventana de repetición: dentro, denegado repetido, límite de 60 s, otra cámara, cambia el resultado y desconocidos. En MQTT, la repetición de un `permitido` se publica con el evento original y la de un `denegado` no |
| `R7 · <caso>` y `R7 · orden` | Los 15 casos de la regla y que se responde el primer motivo que falla, en el orden de la regla |
| `R9 · <caso>` | Segunda en la misma cámara, sin consentimiento, completa, vence, cancelar, otra cámara y vencida sin revisar |
| `contrato cámara · <fila>` | Cada fila de las tablas de resultados y de errores de `api-dispositivo.md`, el orden de las comprobaciones y el último contacto |
| `contrato cámara · cuadro` y `R7 · tolerancia de tamaño con un cuadro` | El cuadro completo (contrato cámara 1.3): el recorte de la cara más grande con la fórmula, `CARA_MIN_PX` sin el 0,8, sin cara, la inscripción, la cabecera `recorte` o ninguna, el tope de 100 KB, el orden de la cabecera y la línea INFO |
| `contrato cámara · modo extraer` | Cada segundo, con 3 s de espera y 3 s después de un evento, como la cámara; el recorte sale del cuadro con la fórmula del contrato y va por `rostros.procesar`, con su `firmware` |
| `RF-10 · C4` | Una cámara de respaldo, falsa y sin red: permitido, desconocido e inscripción; sin cara o con una cara pequeña, nada; las fallas de la URL (tiempo, conexión, 4xx, 5xx, 3xx, no JPEG, más del tope, otro esquema) sin tumbar el bucle, con espera creciente y un aviso por motivo; desactivada, borrada o de otro tipo deja de pedirse, y una URL nueva se usa sin reiniciar; las cámaras en paralelo y las nuevas sin reiniciar; el evento en MQTT, y nada publicado si la transacción no se confirma |
| `contrato recorte · <caso>` | Los casos de `casos-recorte.json` con `caja_del_recorte` y `recortar_cara_mas_grande`, como en el firmware y el simulador |
| `contrato API · abrirInscripcion`, `verInscripcion` y `cancelarInscripcion` | Esquema `Inscripcion`, 404, 409 y 422 |
| `RF-02 · C4` | Sin consentimiento vigente no se abre una inscripción |
| `RF-04 · C1`, `C2` y `C4` | SFace real da 128 números con norma 1; con fotos reales, cada una da una cara y se parece a otra de la misma persona; la imagen se lee en memoria |
| `RF-05 · C1` y `C2` | Se guarda evento salvo en las repeticiones de R4, los descartados y la inscripción |
| `R5 · <caso>` | Los 15 casos de la regla con el reloj de las pruebas: los de la cámara de punta a punta (los de «Clase IA», también con la función pura) y los manuales por la API |
| `R8 · fecha local` | `2026-11-21T03:30:00Z` es una llegada del 20 |
| `R4 · no cambia la asistencia` | Una repetición a las 00:00:20 no crea la llegada del día siguiente |
| `RF-06 · C1` y `C2` | La llegada desde la cámara, con su evento, y la línea INFO que la dice; `reconocer` devuelve la llegada que creó (para B2) y nada en las entradas siguientes |
| `RF-06 · C3` | El reporte separa a tiempo, tarde, sin horario y ausentes: sin inactivas ni personas sin bloque ese día, y con la colación española |
| `RF-06 · C4` | El CSV de un rango, con las columnas del contrato y protegido contra fórmulas |
| `RF-06 · C5` | Registro manual: 404, 422 por hora futura, también para una persona inactiva, y dos registros a la vez, con dos conexiones reales, dejan una sola llegada |
| `RF-05 · C3` | Accesos: filtros por fechas (con sus bordes), resultado, persona y cámara; paginación; orden con empates |
| `RF-12 · C1` y `C3` | Borrar todas las huellas de una persona o una sola; las llegadas de una persona por rango, de la más reciente a la más antigua |
| `RNF-01 · C1` y `C3` | Procesar recortes, también los del modo extraer, no escribe archivos ni registra la imagen (falla si se llama a `cv2.imwrite`); un desconocido y un `parece_otra_persona` no nombran a nadie más, tampoco en el Evento de MQTT |
| `modelos · SHA-256` | Un modelo que no coincide con su tamaño o su SHA-256 no se acepta ni queda en la carpeta |
| `registro · INFO` | Un aviso INFO de `accesia` sale en la salida de errores del proceso, con la hora de Colombia |
| `contrato MQTT · acl` | Mosquitto con el `mosquitto.conf` y la ACL del repositorio: rechaza la conexión anónima, deja entrar a los tres usuarios, y la cámara solo publica en los temas de su client id, nunca en `accesia/servidor/…` |
| `contrato MQTT · disponible` | `online` retenido al conectarse, `offline` al apagarse y el último deseo si la conexión se corta, con QoS 1 |
| `contrato MQTT · evento` | El Evento de `permitido` (con la llegada que creó), `denegado` y `desconocido`, con QoS 1 y sin retener. Un evento que se deshace, o cuya transacción no se confirma, no se publica. Sin conexión no se publica ni queda para después |
| `contrato MQTT · repetido` | Solo la repetición de un `permitido` se publica |
| `R6 · <caso>` | Los siete casos de la regla por la cámara, con el reloj de las pruebas, y una sola alerta por ventana |
| `contrato MQTT · alerta` | La Alerta con su mensaje, QoS 1 y sin retener |
| `contrato MQTT · resumen` | El Resumen al conectarse (con la última llegada por hora y `null` sin llegadas), después de cada evento guardado y de cada llegada manual, y el de cada 5 minutos, que cambia de día a medianoche; retenido y con QoS 1 |
| `contrato MQTT · descubrimiento` | Los seis config de una cámara y los cuatro del servidor, iguales a los de `mqtt.md`, retenidos y con QoS 1; con guiones, el mismo dispositivo de la placa |
| `RF-07 · C1` | El arranque real de la app (su ciclo de vida) se conecta, publica el descubrimiento y el resumen, y al apagarse deja `offline`. El descubrimiento sale también al conectarse, cuando Home Assistant vuelve a estar en línea (no con `offline`), al crear o editar una cámara por la API y con `crear-camara`, también sin broker |
| `contrato MQTT · limpieza del descubrimiento` | Se borran los config de cámaras que ya no existen; los de la placa, los de una cámara que existe y los del servidor quedan |

Las pruebas del agente usan la hora fija de `pruebas/hora_fija.py` (viernes 2026-11-20 a las 10:00) y una semilla guardada de verdad en la base de prueba, porque el usuario `agente` no ve lo que otra conexión no confirmó; al terminar cada módulo se borra.

La CI corre `uv run pytest` en cada PR y en cada push a `main` (`.github/workflows/servidor.yml`), con los modelos de cara en caché.
