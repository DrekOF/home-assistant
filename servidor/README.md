<!--
Nombre: README.md
Descripción: Servidor de AccesIA: API, reconocimiento, reglas, MQTT y MCP (frente B).
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.5
-->

# Servidor · frente B

Python 3.13 con FastAPI: saca la huella de la cara (YuNet + SFace), aplica las reglas, guarda en PostgreSQL con pgvector, publica en MQTT, sirve la web y, con otro comando, el servidor MCP del agente.

- Specs: `specs/arquitectura.md`, `specs/reglas.md`, `specs/modelo-datos.md` y todos los contratos.
- Lo crea la tarea `tareas/dia-1/B-cristhian-compose-y-base.md`. La tarea B1 del Día 2 suma la sesión y la API de administración; B2, el reconocimiento y la inscripción. Del Día 3, B1 suma la asistencia (R5) y la API de consulta, y B3 el servidor MCP del agente y su semilla; MQTT es de B2.

## Qué hay

| Ruta | Qué es |
| --- | --- |
| `accesia/config.py`, `db.py`, `tiempo.py` | Variables de `arquitectura.md`; motor de la base y una transacción por petición; hora de Colombia (R8) |
| `accesia/errores.py` y `esquemas.py` | El esquema `Error` y los esquemas de `openapi.yaml` 1.3 con pydantic |
| `accesia/sesion.py` y `seguridad.py` | Cookie de sesión firmada, primer administrador, Argon2id para las claves y SHA-256 para los tokens |
| `accesia/consentimiento.py` y `camaras.py` | Texto del consentimiento y la lógica de las cámaras que comparten la API y el comando |
| `accesia/modelos.py` y `vision.py` | YuNet y SFace fijos con su SHA-256, su nombre corto y su descarga; la visión solo en memoria: decodificar, detectar, recortar con la fórmula del contrato, huella y nitidez |
| `accesia/rostros.py`, `reconocimiento.py` e `inscripciones.py` | Lo que llega de la cámara (`enviarRostro`): comprobaciones en orden, 429 en memoria y el modo; R1 a R5 y R7 al reconocer; inscripciones (R9) y los seis pasos de R7 |
| `accesia/asistencia.py` | R5 y R8: califica una llegada con el bloque del día (función pura) y registra la primera del día. La usan la cámara, el registro manual y la semilla del agente |
| `accesia/mensajes.py` y `registro.py` | Las frases del campo `mensaje`; los avisos INFO en el registro, con la hora de Colombia |
| `accesia/api/` | Rutas: `salud`, `sesion`, `personas`, `consentimiento`, `horarios`, `camaras`, `rostros`, `inscripciones`, `huellas`, `accesos`, `asistencia` y `configuracion` |
| `accesia/agente.py` | Las cinco herramientas del agente (`mcp-agente.md`): consultas sobre las tres vistas del agente, cada una en una transacción `READ ONLY` de 3 s, que devuelven lo del contrato o `{"error": …}` |
| `accesia/servidor_mcp.py` | El servidor MCP «AccesIA» con el SDK `mcp` 2.x (`MCPServer`): Streamable HTTP en `/mcp`, puerto 8001, sin sesiones y con el encabezado `Host` validado |
| `accesia/semilla.py` | `semilla agente`: los datos de la evaluación del agente, la revisión de las preguntas 1 a 9 y cómo convive con datos reales |
| `accesia/comandos.py` | El comando `accesia`: `crear-camara`, `descargar-modelos`, `mcp` y `semilla agente` |
| `accesia/main.py` | La aplicación: al arrancar exige `SESION_SECRETO`, crea el primer administrador y carga los modelos de cara |
| `migraciones/` | Alembic. La migración `0001` ejecuta tal cual `specs/contratos/base-de-datos.sql` y crea el usuario `agente` |
| `pruebas/` | pytest con PostgreSQL 18 + pgvector y Mosquitto en contenedores (testcontainers); `armar.py` arma datos en la base, `vision_falsa.py` arma caras y huellas sin fotos y `hora_fija.py` fija la hora de las pruebas del agente |
| `Dockerfile` | Imagen multietapa con uv; se construye desde la raíz del repositorio, copia el SQL del contrato y `specs/consentimiento.md`, y descarga los modelos de cara comprobando su SHA-256 |
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

## Reconocimiento e inscripción

`POST /api/v1/dispositivos/{codigo}/rostros` (`enviarRostro`) no usa la sesión: la cámara se identifica con su token Bearer, que se compara por su SHA-256 con `hmac.compare_digest`. Las comprobaciones van en este orden y se responde la primera que falla:

| Orden | Respuesta | Cuándo |
| --- | --- | --- |
| 1 | 401 `token_invalido` | Falta el token, no corresponde o la cámara no existe; no se dice cuál de las tres |
| 2 | 403 `dispositivo_inactivo` | La cámara está desactivada |
| 3 | 415 `tipo_no_soportado` | El `Content-Type` no es `image/jpeg` (se aceptan parámetros y mayúsculas) |
| 4 | 413 `imagen_grande` | El cuerpo pasa de 100 KB, es decir de 102 400 bytes (contrato cámara 1.2); se corta sin leerlo entero |
| 5 | 429 `demasiadas_peticiones` | Llegaron dos recortes de esa cámara con menos de 0,8 s; lleva `Retry-After: 1`. Cuenta desde el último recorte aceptado: un 429 no mueve el reloj |
| 6 | 422 `imagen_invalida` | El cuerpo no es un JPEG que se pueda leer |

- Desde el paso 2, toda petición guarda `ultimo_contacto`, aunque falle después.
- La imagen solo vive en memoria: no se escribe en disco ni aparece en el registro (RNF-01).
- Antes de decidir el modo, la inscripción de la cámara vence si ya pasó su hora (R9). Con una inscripción activa, la cámara inscribe (los seis pasos de R7); si no, reconoce (R1 a R4).
- R1 compara con el umbral con una tolerancia de 1e-6, porque pgvector calcula en float32 (`specs/reglas.md`).
- Una repetición de R4 devuelve el resultado, el motivo, la persona y el `evento_id` del evento original, con la similitud del recorte nuevo, y no guarda nada.
- `accesia/vision.py` deja lista `recortar_cara_mas_grande`: detecta con YuNet en un cuadro completo, elige la cara de mayor área y recorta con la fórmula del contrato. La usarán una cámara que envíe cuadros completos y el modo extraer (RF-10 · C4).

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

## Servidor MCP del agente

`accesia mcp` arranca el servidor MCP «AccesIA» de `specs/contratos/mcp-agente.md` 1.3. En Compose lo corre el servicio `mcp`, con la misma imagen del servidor.

- **SDK y transporte.**
  - Usa el SDK oficial `mcp` 2.x, donde FastMCP se llama `MCPServer`.
  - Sirve Streamable HTTP en `http://0.0.0.0:8001/mcp`, sin sesiones y con respuestas JSON: cada pedido es independiente, así que si el contenedor se reinicia, Home Assistant no queda con una sesión vieja.
  - No pide autenticación (D-16).
- **Solo lectura, en tres capas (D-15).**
  - Solo arranca si `DATABASE_URL` usa el usuario `agente`, que solo lee las tres vistas del agente. Con otro usuario sale con un error.
  - Cada herramienta corre en su propia transacción `READ ONLY`, con `statement_timeout` de 3 s.
  - Las cinco herramientas solo consultan, y se anuncian con `readOnlyHint`.
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

## Rutas

Todas piden sesión (401 `sin_sesion` sin ella), menos `GET /api/v1/salud`, `POST /api/v1/sesion` y `POST /api/v1/dispositivos/{codigo}/rostros`, que usa el token de la cámara. `DELETE /api/v1/sesion` responde 204 haya sesión o no.

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

Las reglas se prueban con la visión armada de `pruebas/vision_falsa.py` (caras con puntaje, tamaño, nitidez y huella elegidos, sin fotos) y PostgreSQL real. La fixture `reloj` controla `accesia.tiempo.ahora()` en todos los módulos, y cada cámara de prueba avanza 1 s el reloj del 429 en cada recorte. Las pruebas con caras reales leen las fotos `<persona>-<n>` de `datos/prueba/`, la carpeta del modo carpeta del simulador, sin las que `esperado.json` marca como no enviadas; sin fotos se saltan, y en la CI siempre se saltan.

| Marca | Qué comprueba |
| --- | --- |
| `contrato BD · esquema` | La base migrada tiene las mismas tablas, columnas, restricciones, índices, vistas y permisos que el contrato cargado aparte |
| `contrato BD · vector` | La búsqueda central de `modelo-datos.md` devuelve la muestra más parecida (R2) |
| `contrato BD · horarios` | Horarios por bloques (D-20): cinco bloques en «Clase IA», un bloque por día, borrado en cascada, `restrict_violation` (23001) al borrar uno en uso y días de la vista del agente |
| `RF-08 · C4` | El usuario `agente` lee sus tres vistas y no puede leer `persona`, `rostro` ni `horario_bloque`, ni cambiar las tablas. Cada herramienta corre en una transacción de solo lectura con 3 s de límite, y el servidor MCP no arranca con otro usuario |
| `contrato agente · <herramienta>` | Las cinco herramientas con los datos de la semilla y el usuario `agente`: lo que devuelven, sus límites (10 personas, 31 días, 50 accesos, de 1 a 168 horas y 10 en `ultimos`) y sus errores como `{"error": …}` |
| `contrato agente · preguntas` | Las preguntas 1 a 9 de la evaluación, cada una con su herramienta esperada |
| `contrato agente · evaluación` | `semilla agente` crea la tabla de la evaluación con fechas relativas a hoy; con datos reales no escribe sin `--con-datos-reales` y nunca los toca; se repite y se borra sola |
| `contrato agente · host` | El servidor MCP acepta el `Host` de `mcp:8001`, `localhost:8001`, `127.0.0.1:8001` y `MCP_HOSTS_PERMITIDOS`; otro `Host` recibe 421 y un pedido con `Origin`, 403 |
| `RF-08 · C1` | Un cliente MCP real, por Streamable HTTP contra el servidor en uvicorn, lista las cinco herramientas (en español y de solo lectura) y las llama |
| `RNF-01 · C4` | Ninguna respuesta de las herramientas trae documentos, huellas ni similitudes |
| `contrato API · salud` | `GET /api/v1/salud` cumple el esquema `Salud` y da la hora con `-05:00` |
| `contrato API · error` | Validación, ruta inexistente, método no permitido (405 con `Allow`) y error interno responden con el esquema `Error` |
| `contrato API · <operationId>` | Cada operación de sesión, personas, consentimiento, horarios, cámaras, huellas, accesos, asistencia y configuración responde con su esquema y con los códigos de error del contrato |
| `contrato API · inscripcion_activa` | Una cámara muestra su inscripción activa y `modo: inscribir`; si ya pasó su hora, la vence y el campo queda en `null` (R9) |
| `RNF-02 · C2` | Cookie `HttpOnly`, `SameSite=Strict`, `Path=/` y de 8 horas; primer administrador con Argon2id; sin `SESION_SECRETO` no arranca |
| `RNF-02 · C5` | Cada ruta con sesión responde 401 `sin_sesion` sin cookie, con una firma falsa, con una cookie vencida o con el administrador desactivado |
| `RF-02 · C1`, `C2` y `C5` | Documento único, activar y desactivar; consentimiento con versión, medio, autor y fecha; revocar borra las huellas |
| `RF-10 · C1`, `C2`, `C3` y `C5` | Token mostrado una vez y guardado como SHA-256, cambio de token, en línea por el último contacto y el comando `crear-camara` |
| `RF-12 · C2` | Borrar una persona borra lo suyo y deja sus eventos sin persona |
| `RF-13 · C1`, `C2` y `C3` | Horarios por bloques, reemplazo de bloques y `horario_en_uso` |
| `R8 · formato` | Las fechas de la API salen en ISO 8601 con `-05:00` |
| `R9 · revoca a mitad` y `R9 · desactivar no cancela` | Revocar cancela la inscripción activa y borra sus huellas, y la siguiente cara se reconoce; desactivar a la persona no la cancela |
| `R1 · <caso>`, `R2 · <caso>` y `R3 · <caso>` | Umbral (también 0,363 menos un paso de float32), la muestra más parecida y el estado de la persona, con `revocado de punta a punta` por la API |
| `R4 · <caso>` | Ventana de repetición: dentro, denegado repetido, límite de 60 s, otra cámara, cambia el resultado y desconocidos (la publicación en MQTT es del Día 3) |
| `R7 · <caso>` y `R7 · orden` | Los 15 casos de la regla y que se responde el primer motivo que falla, en el orden de la regla |
| `R9 · <caso>` | Segunda en la misma cámara, sin consentimiento, completa, vence, cancelar, otra cámara y vencida sin revisar |
| `contrato cámara · <fila>` | Cada fila de las tablas de resultados y de errores de `api-dispositivo.md`, el orden de las comprobaciones y el último contacto |
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
| `RNF-01 · C1` y `C3` | Procesar recortes no escribe archivos ni registra la imagen (falla si se llama a `cv2.imwrite`); un desconocido y un `parece_otra_persona` no nombran a nadie más |
| `modelos · SHA-256` | Un modelo que no coincide con su tamaño o su SHA-256 no se acepta ni queda en la carpeta |
| `registro · INFO` | Un aviso INFO de `accesia` sale en la salida de errores del proceso, con la hora de Colombia |
| `contrato MQTT · acl` | Mosquitto con el `mosquitto.conf` y la ACL del repositorio: rechaza la conexión anónima, deja entrar a los tres usuarios, y la cámara solo publica en los temas de su client id, nunca en `accesia/servidor/…` |

Las pruebas del agente usan la hora fija de `pruebas/hora_fija.py` (viernes 2026-11-20 a las 10:00) y una semilla guardada de verdad en la base de prueba, porque el usuario `agente` no ve lo que otra conexión no confirmó; al terminar cada módulo se borra.

La CI corre `uv run pytest` en cada PR y en cada push a `main` (`.github/workflows/servidor.yml`), con los modelos de cara en caché.
