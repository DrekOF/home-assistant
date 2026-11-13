<!--
Nombre: requisitos.md
Descripción: Requisitos funcionales y no funcionales de AccesIA con sus criterios de aceptación.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.5
-->

# Requisitos

Cada requisito tiene criterios de aceptación (C1, C2…). Una prueba cita el requisito y el criterio, por ejemplo `RF-04 · C2`. Las metas marcadas como propuesta las confirma el equipo con las pruebas.

## Requisitos funcionales

### RF-01 Detección en la cámara (TinyML) · frente A

Con el hardware de D-21, la placa todavía no tiene cámara y RF-01 queda pendiente del módulo que llega la próxima clase. Mientras tanto lo cumplen el simulador (C6) y, como referencia, el firmware del ESP32-S3 del PR #7.

- C1 Detecta caras dentro del ESP32-S3 con `espressif/human_face_detect` (MSR + MNP, int8).
- C2 Envía solo el recorte en JPEG, con la fórmula del recorte de `contratos/api-dispositivo.md`, y espera al menos 1 s desde cada respuesta antes de enviar otro.
- C3 No envía nada si no hay cara o si la cara mide menos de `CARA_MIN_PX` de alto.
- C4 Se configura por consola serial sin recompilar (`arquitectura.md`).
- C5 Compila los dos binarios, `octal` y `quad`, con todos sus perfiles de placa (D-17).
- C6 El simulador cumple el mismo contrato y pasa las mismas pruebas de contrato, incluidos los casos de `contratos/casos-recorte.json`.

### RF-02 Personas y consentimiento · frentes B y C

- C1 Crear, ver, editar, activar y desactivar personas. El documento es único.
- C2 Registrar el consentimiento con la versión del texto, el medio (web o papel), quién lo registró y la fecha.
- C3 La web muestra el texto de `consentimiento.md`, dice que es opcional y ofrece el registro manual de asistencia como alternativa (RF-06 · C5).
- C4 Sin consentimiento vigente no se puede abrir una inscripción (422, código `sin_consentimiento`).
- C5 Revocar el consentimiento borra las huellas de la persona y cancela su inscripción activa, en la misma transacción.

### RF-03 Inscripción · frentes B y C

- C1 La web abre una inscripción para una persona y una cámara.
- C2 Mientras está activa, cada cara de esa cámara se revisa con R7: las válidas se guardan como muestras y las demás se rechazan con su motivo.
- C3 Con `INSCRIPCION_MUESTRAS` muestras queda completada y la cámara vuelve a reconocer.
- C4 Vence a los `INSCRIPCION_VENCE_S` segundos; las muestras aceptadas se conservan.
- C5 Solo hay una inscripción activa por cámara (409, código `inscripcion_activa`) y se puede cancelar.
- C6 La web muestra el avance (por ejemplo, 3 de 5) y el motivo del último rechazo.

### RF-04 Reconocimiento · frente B

- C1 Saca la huella con YuNet + SFace: 128 números normalizados.
- C2 La compara con todas las muestras con pgvector (distancia de coseno) y toma la más parecida (R2).
- C3 Aplica R1, R3 y R4 y responde según `contratos/api-dispositivo.md`.
- C4 La imagen solo vive en memoria mientras se procesa (RNF-01).
- C5 Responde en menos de 1 s en el portátil y en menos de 2 s en la Raspberry (meta propuesta).

### RF-05 Registro de accesos · frentes B y C

- C1 Cada intento con resultado `permitido`, `denegado` o `desconocido` guarda un evento, salvo las repeticiones de R4.
- C2 Los recortes con resultado `descartado` no guardan evento.
- C3 La API y la web listan los eventos por fechas, resultado, persona y cámara, con paginación.

### RF-06 Asistencia · frentes B y C

- C1 La primera entrada permitida del día crea la asistencia con su hora de llegada y su estado (R5).
- C2 Las entradas siguientes del mismo día no cambian la llegada.
- C3 El reporte del día separa a tiempo, tarde, sin horario y ausentes (personas activas cuyo horario tiene bloque ese día y sin llegada).
- C4 Exportar a CSV por rango de fechas (extra).
- C5 Registro manual: un administrador registra la llegada de una persona a una hora dada (`POST /api/v1/asistencia`). Se aplica R5 a esa hora y responde 409 `asistencia_duplicada` si ya tiene llegada ese día. La llegada queda con origen `manual` y con quién la registró. Sirve para quien no dio consentimiento y como plan B si la cámara falla.

### RF-07 Home Assistant · frentes B (publicación) y C (configuración)

- C1 Las entidades de `contratos/mqtt.md` aparecen solas al arrancar el servidor y cada vez que Home Assistant avisa que está en línea. Las de temperatura y humedad las publica la placa al conectarse (D-21).
- C2 Con un acceso permitido, también si es una repetición de R4, la automatización abre la puerta y la entidad Puerta cambia en menos de 2 s (meta propuesta).
- C3 Con la alerta de R6, Home Assistant crea una notificación de desconocidos.
- C4 Hay un panel «Portería» con última persona, último resultado, asistentes hoy, llegadas tarde hoy, desconocidos, puerta y cámara en línea.

### RF-08 Agente · frentes B (MCP) y C (Home Assistant)

- C1 Las 5 herramientas de `contratos/mcp-agente.md` funcionan por MCP.
- C2 Se usan desde Assist con el agente de Ollama.
- C3 Responde bien al menos 9 de las 10 preguntas de evaluación; la 9 y la 10 son obligatorias.
- C4 No puede escribir: el usuario `agente` falla al insertar, actualizar o borrar, y al leer las tablas directamente.
- C5 No puede operar la puerta: «Control de dispositivos» queda apagado en el agente (D-15).

### RF-09 Web de administración · frente C

- C1 Inicio de sesión de administradores; las demás pantallas piden sesión.
- C2 Pantallas: Personas (con consentimiento), Inscripción (avance en vivo), Accesos, Asistencia (con registro manual), Cámaras y Horarios (RF-13).
- C3 Hecha con los skills de frontend y verificada con Playwright: se ve y funciona como se planeó.
- C4 Textos en español; fechas y horas en hora de Colombia.

### RF-10 Cámaras · frentes B y C

- C1 Registrar una cámara (código, nombre y tipo). El token se muestra una sola vez y se guarda como hash.
- C2 Cambiar el token; el anterior deja de servir.
- C3 Ver el último contacto y si está en línea.
- C4 Modo extraer: para una cámara de tipo `respaldo`, el servidor pide `GET {url_captura}` cada segundo, detecta y recorta la cara y la procesa como si hubiera llegado de la cámara.
- C5 Comando `crear-camara` del servidor: registra una cámara (código, nombre y tipo) y muestra su token una sola vez, sin pasar por la web. Sirve para el Hito 1 y como plan B.

### RF-11 Kit del día de clase · frente C, con A y B

- C1 Scripts `instalar` y `verificar`. Con D-22, `verificar` revisa la Pi desde el portátil: los complementos, MQTT, las entidades en Home Assistant, Ollama y la placa en línea. `instalar` queda para los planes B y C (el portátil y el escenario 1).
- C2 Las carpetas de los complementos `accesia_base` y `accesia_servidor`, con los modelos de cara; los archivos del modelo de Ollama, para copiarlos a la Pi sin internet; la copia de seguridad cifrada de Home Assistant OS, sin inscripciones; el binario del firmware de la XIAO ESP32-C6 y esptool (D-21 y D-22). Para el plan B, las imágenes de Docker del portátil; para el plan C, las imágenes arm64 en archivos `.tar`. Los binarios del ESP32-S3 (`octal` y `quad`), el de diagnóstico y el de respaldo quedan como referencia.
- C3 Ensayo desde cero hasta la primera persona reconocida en menos de 45 minutos (meta propuesta).

### RF-12 Derechos del titular (Ley 1581) · frentes B y C

- C1 Borrar todas las huellas de una persona.
- C2 Borrar una persona: se borran sus huellas, consentimientos, inscripciones y asistencia; sus eventos quedan sin persona.
- C3 Ver qué datos hay de una persona en su ficha, sin mostrar las huellas: sus datos, sus consentimientos (el vigente y los revocados), cuántas muestras tiene, sus accesos y su asistencia (`GET /api/v1/personas/{persona_id}/asistencia`).

### RF-13 Horarios · frentes B y C

- C1 Crear, ver, editar y borrar horarios. Cada horario tiene un nombre y bloques: día (1 = lunes … 7 = domingo), hora de inicio y tolerancia en minutos, con al menos un bloque y uno por día como máximo (D-20).
- C2 Editar los bloques de un horario reemplaza la lista completa.
- C3 Un horario en uso no se puede borrar (409, código `horario_en_uso`).
- C4 Una persona tiene un horario o ninguno, y R5 califica cada llegada con el bloque del día.
- C5 La web tiene la pantalla Horarios: la lista y un formulario con un renglón por día (activo, hora y tolerancia).

### RF-14 Placa del punto de acceso (XIAO ESP32-C6) · frente A

- C1 Un solo binario para la XIAO ESP32-C6, que compila en GitHub Actions con `firmware.yml` (D-21).
- C2 Al arrancar enciende el conmutador de antena (GPIO3 en bajo) y elige la antena configurada: GPIO14 en bajo para la interna y en alto para la externa. El comando `antena` la cambia.
- C3 Cada 30 s lee el sensor (DHT22 por defecto; DHT11 con el comando `sensor`) y publica la temperatura y la humedad en `accesia/{codigo}/ambiente`. Tras 3 lecturas fallidas seguidas publica `null`.
- C4 Publica el descubrimiento de sus dos sensores: Temperatura y Humedad aparecen en Home Assistant aunque el servidor esté apagado, y quedan no disponibles si la placa se desconecta.
- C5 Con `ABRIR` enciende el LED (GPIO15, que enciende en bajo) los segundos configurados y publica `abierta` y luego `cerrada`. El resto del tiempo el LED muestra el estado de la placa.
- C6 Se configura por consola serial sin recompilar: Wi-Fi, servidor, código, token, MQTT, puerta con su nivel, sensor y antena.

## Requisitos no funcionales

### RNF-01 Privacidad

- C1 Nunca se guarda una imagen de cara: ni en disco, ni en la base, ni en los registros, ni en el repositorio.
- C2 Prueba: después de una sesión de pruebas no hay archivos de imagen en los volúmenes ni imágenes en base64 en los registros.
- C3 A un desconocido no se le dice a quién se parece. Al inscribir, una muestra rechazada por parecerse a otra persona tampoco dice a quién.
- C4 El agente no ve documentos ni huellas.

### RNF-02 Seguridad

- C1 La cámara se autentica con un token Bearer que el servidor guarda como hash.
- C2 La web usa una cookie de sesión `HttpOnly` y `SameSite=Strict`; las contraseñas se guardan con Argon2.
- C3 MQTT no admite acceso anónimo y tiene ACL por usuario.
- C4 No hay claves en el repositorio.
- C5 Sin token o sin sesión, la API responde 401.
- C6 Se prueba una foto impresa frente a la cámara y se documenta el resultado: no hay detección de vida (límite conocido).

### RNF-03 Rendimiento (metas propuestas)

- C1 Respuesta a la cámara en menos de 1 s en el portátil y de 2 s en la Raspberry.
- C2 Puerta abierta en menos de 2 s desde que llega el recorte.
- C3 Se mide la respuesta de Assist en la Raspberry con el modelo elegido (D-22). Si pasa de 15 s, primero se prueba en la Pi: las variantes Q4_0 del modelo, descripciones más cortas de las herramientas, `qwen2.5:0.5b` si responde bien, y que el comienzo del prompt no cambie entre preguntas (`arquitectura.md`, «Velocidad del agente en la Pi»). Pasar Ollama al portátil, con `infra/compose.ollama-portatil.yaml`, solo vale con el visto bueno del profesor, que pide Ollama dentro de la Pi.

### RNF-04 Portabilidad

- C1 Imágenes para arm64 y amd64.
- C2 Corre en Windows con Docker Desktop, en Raspberry Pi OS de 64 bits y como complementos de Home Assistant OS. En la demo (D-22), todo corre en la Pi como complementos; Docker Compose en el portátil con Windows queda para desarrollar y como plan B.
- C3 En clase no necesita internet. La excepción es instalar los complementos en la Pi, que baja las imágenes base y los paquetes de Python: si la Pi solo está disponible en clase, se instala allá con el internet del celular (D-22). Los modelos van en el kit.

### RNF-05 Idioma y hora

- C1 Dominio, API, mensajes y web en español.
- C2 Hora de Colombia; en la API y en MQTT, ISO 8601 con zona (R8).

### RNF-06 Calidad

- C1 Cada requisito y cada regla tiene pruebas que citan su código.
- C2 Un PR se fusiona solo con las pruebas en verde.
- C3 GitHub Actions corre las pruebas en cada PR desde el Día 1, en un workflow por pieza para no chocar: `.github/workflows/servidor.yml` (pytest, tarea B) y `.github/workflows/web.yml` (build y Vitest, tarea C). Desde el Día 2 se suma `.github/workflows/simulador.yml` (pytest del simulador con el modelo YuNet en caché, tarea A). El firmware se suma con `.github/workflows/firmware.yml`, que D-21 adelanta: compila el binario de la XIAO ESP32-C6 y corre las pruebas de la lógica pura. Con D-22 se suma `.github/workflows/complementos.yml` (B4 del Día 4): construye los dos complementos para arm64 y amd64 y arranca los de amd64. Como `main` no está protegida, la regla de fusionar solo en verde se cumple por disciplina.

### RNF-07 Precisión del reconocimiento (meta propuesta)

- C1 Con los 3 integrantes, 20 intentos cada uno, y fotos de un dataset público como impostores: ningún impostor aceptado y máximo 2 rechazos de 20 por persona. Los recortes son como los de la cámara real: del ESP32-S3 o del simulador en modo «como la cámara».
- C2 El umbral final y los resultados quedan anotados en `decisiones.md`.
