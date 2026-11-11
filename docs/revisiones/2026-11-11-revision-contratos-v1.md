<!--
Nombre: 2026-11-11-revision-contratos-v1.md
Descripción: Revisión de las specs y los contratos 1.0 de AccesIA (tarea 00 del Día 1), hecha con Claude Code.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Revisión de specs y contratos de AccesIA (tarea 00, Día 1)

- Fecha: 2026-11-11. Contratos revisados en versión 1.0.
- Pedido: «Lee CLAUDE.md, specs/README.md y todos los archivos de specs/ y specs/contratos/. No escribas código ni cambies archivos. Dime: 1) inconsistencias entre los contratos o con las specs, 2) huecos que impidan empezar las tareas del Día 1, 3) riesgos técnicos. Sé concreto: archivo, sección y propuesta.»
- Qué se leyó: `CLAUDE.md`, las 9 specs, los 6 archivos de `specs/contratos/` y, para el punto 2, las 4 tareas de `tareas/dia-1/`, `.gitignore` y `.editorconfig`.
- No se cambió ningún archivo del repositorio. Según `CLAUDE.md`, un contrato cambia solo por PR, con la aprobación de los frentes que lo usan y una línea en `specs/decisiones.md`.
- Página publicada (privada; se comparte desde su menú Compartir): https://claude.ai/artifact/VohHhx1gX6p8ACrss5Aqaa
- Resumen: 12 inconsistencias, 7 huecos y 11 riesgos; 7 de prioridad alta.

## Lo más urgente

- 2.1 Proteger `main` en un repo privado no se puede con GitHub Free.
- 1.1 Una cámara con código `servidor` choca con el servidor.
- 1.3 Falta el registro manual de asistencia.
- 2.3 La fórmula del recorte no está escrita.
- 2.4 El SQL del contrato no entra en la imagen Docker.

## Preguntas para agregar a la tarea 00 (siguen a las 5 que ya trae)

6. ¿GitHub Pro con el Student Developer Pack o repo público? (2.1)
7. ¿Qué pasa con la puerta en una repetición de R4? (1.7)
8. ¿Binarios por tipo de PSRAM o por placa? (1.8)
9. ¿El registro manual de asistencia va en la API o fuera del sistema? (1.3)
10. ¿Se agrega a R7 el paso 6? (3.7)
11. ¿Alguien consigue una placa antes de la clase? (3.1)

## 1. Inconsistencias

### 1.1 Una cámara con código `servidor` choca con el servidor · Alta · frentes A, B y C
- Dónde: `specs/contratos/mqtt.md` § Temas (línea 43), § Entidades (línea 125) y ACL del usuario `camara` (líneas 32-36); `specs/contratos/base-de-datos.sql:64` (`dispositivo.codigo`).
- Problema: el patrón `^[a-z0-9-]{3,32}$` acepta `servidor`. Esa cámara publicaría en `accesia/servidor/disponible`, que es el tema del servidor, y su «Cámara en línea» tendría el mismo `binary_sensor.accesia_servidor_en_linea` que «Servidor en línea». Además, la regla `write accesia/+/disponible` deja que cualquier cámara publique `offline` en nombre del servidor y apague todas sus entidades en Home Assistant.
- Propuesta: reservar `servidor` (CHECK en el SQL y 422 en la API). En la ACL, usar `pattern write accesia/%c/…` y `pattern read accesia/%c/puerta/set`, con el client id de MQTT igual al código de la cámara.

### 1.2 El caso «R3 · sin consentimiento» no se puede dar de verdad · Media · frente B
- Dónde: `specs/reglas.md:57` (caso «R3 · sin consentimiento»); `specs/requisitos.md:31` (RF-02 · C5).
- Problema: revocar el consentimiento borra las huellas en la misma transacción. Bruno, con el consentimiento revocado, ya no coincide con nadie: sale `desconocido`, no `denegado` con `sin_consentimiento`. El caso solo se da con datos armados a mano.
- Propuesta: dejar R3 como defensa y aclarar que su prueba arma el estado directamente en la base. Agregar un caso de punta a punta: se revoca y la siguiente cara sale `desconocido`.

### 1.3 El registro manual de asistencia no existe · Alta · frentes B y C · decisión del equipo
- Dónde: `specs/consentimiento.md:28`; `specs/requisitos.md:29` (RF-02 · C3) y `:102` (RF-12 · C3); `specs/decisiones.md:24` (D-07); `specs/contratos/openapi.yaml:466` (`/api/v1/asistencia`).
- Problema: el texto del consentimiento promete que, si la persona no autoriza, su asistencia se puede registrar a mano, y la tarea C debe ofrecer esa alternativa. Pero la API solo tiene `GET /api/v1/asistencia` y la tabla `asistencia` no distingue de dónde viene cada llegada. Quien no autorice saldrá siempre en `ausentes`. Tampoco hay forma de ver la asistencia de una sola persona (RF-12 · C3).
- Propuesta: en los contratos 1.1, agregar `POST /api/v1/asistencia` para el registro manual, una columna `asistencia.origen` (`camara` o `manual`) y un filtro `persona_id` en el reporte. Si no alcanza el tiempo, cambiar el texto a «el docente la registra en su lista» y ajustar RF-02 · C3.

### 1.4 El texto del consentimiento no nombra todos los datos · Media · todo el equipo
- Dónde: `specs/consentimiento.md:22` (§ Qué datos).
- Problema: el texto lista nombre, documento, rol, horario y huella. El sistema también guarda cada intento de entrada (fecha, hora, cámara y similitud) y la asistencia del día.
- Propuesta: agregar «y el registro de mis entradas: fecha, hora y cámara» antes de aceptar la versión 1.0. Cambiarlo después obliga a sacar la versión 1.1 y a mostrar qué versión aceptó cada persona.

### 1.5 Una inscripción vencida que nadie revisó bloquea la cámara · Media · frente B
- Dónde: `specs/reglas.md:151` (R9); `specs/contratos/base-de-datos.sql:92` (índice `inscripcion_activa_por_camara`).
- Problema: R9 revisa el vencimiento solo cuando llega una cara o cuando alguien consulta la inscripción. Si no pasa ninguna de las dos, la inscripción sigue `activa`: `POST /api/v1/inscripciones` responde 409 `inscripcion_activa` y la cámara aparece con `modo: inscribir`.
- Propuesta: que abrir una inscripción y listar las cámaras también venzan las que ya pasaron su hora. Caso de prueba `R9 · vencida sin revisar`.

### 1.6 Revocar con una inscripción en curso · Media · frente B
- Dónde: `specs/reglas.md:147` (R9); `specs/requisitos.md:31` (RF-02 · C5).
- Problema: R9 pide el consentimiento vigente solo al abrir la inscripción. Si se revoca a mitad de la sesión, las caras siguientes se guardan como huellas de alguien sin consentimiento.
- Propuesta: revocar cancela la inscripción activa de la persona en la misma transacción. Decidir también qué pasa si se desactiva a la persona.

### 1.7 R4 deja la puerta cerrada en el segundo intento · Alta · todo el equipo · decisión del equipo
- Dónde: `specs/reglas.md:63-65` (R4); `specs/contratos/mqtt.md:166-180` (automatización `accesia_abrir_puerta`).
- Problema: la puerta solo se abre cuando Home Assistant recibe un `evento`, y una repetición de R4 no publica nada. Si Ana no alcanza a pasar en los 3 s y vuelve a mirar la cámara antes de 60 s, recibe `permitido` pero la puerta no se abre. En la demo va a pasar.
- Propuesta: hay dos opciones. (a) Bajar `VENTANA_REPETIDO_S` para la demo y explicarlo. (b) Que un `permitido` repetido publique solo la orden de abrir, sin guardar evento ni tocar la asistencia.

### 1.8 El comando `perfil` choca con «cada perfil es un binario» · Media · frente A · decisión del equipo
- Dónde: `specs/arquitectura.md:109` (§ Perfiles de placa) y `:138` (comando `perfil`); `tareas/dia-1/A-julian-esp-idf-y-deteccion.md:56` (C1).
- Problema: si cada placa tiene su propio binario, el comando `perfil` no tiene nada que cambiar. Los pines de la cámara se configuran al arrancar; lo único que obliga a recompilar es el tipo de PSRAM (D-17).
- Propuesta: un binario por tipo de PSRAM: `octal`, con los cuatro perfiles octales elegibles por consola, y `quad`, con `generico_quad`. Son dos compilaciones en vez de cinco. Cambia el C1 de la tarea A.

### 1.9 El paso 5 de R7 se puede leer de dos formas · Media · frente B
- Dónde: `specs/reglas.md:119` (R7, paso 5).
- Problema: no dice si se mira la muestra más parecida de todas (R2) o la más parecida de otra persona. Ejemplo: al inscribir a Ana, su propia muestra da 0,80 y una de Bruno da 0,50. Con la primera lectura se acepta; con la segunda se rechaza por `parece_otra_persona`.
- Propuesta: buscar con `WHERE persona_id <> :persona` y agregar el caso `R7 · se parece a las dos`.

### 1.10 A quién nombra `parece_otra_persona` · Media · frente B
- Dónde: `specs/contratos/api-dispositivo.md:42` (campo `persona`).
- Problema: el contrato no dice qué persona va en `persona` cuando una muestra se rechaza por parecerse a otra. Si va la otra, la cámara revela a quién se parece la cara.
- Propuesta: escribir que en modo inscribir `persona` es siempre quien se inscribe, y que ni `persona` ni `mensaje` nombran a quien se parece (RNF-01 · C3 aplicado a la inscripción).

### 1.11 Ollama y el MCP fuera de Docker · Media · frentes B y C
- Dónde: `specs/decisiones.md:38` (D-16) y `:41` (D-19); `specs/arquitectura.md:73` (escenario 2); `specs/requisitos.md:126` (RNF-03 · C3).
- Problema: D-16 y D-19 dicen que el MCP y Ollama no se publican fuera de Docker. Pero el escenario 2 los publica en la red del portátil, y RNF-03 · C3 manda Ollama al portátil si la Raspberry tarda más de 15 s, también en el escenario 1, sin un archivo de Compose para eso.
- Propuesta: anotar la excepción en D-16 y D-19, y preparar un Compose para el portátil que solo levante `ollama` publicado en la red propia.

### 1.12 Menores · Baja · frentes A, B y C
- `.gitignore:40` ignora `firmware/**/build/`, pero la tarea A compila en `firmware/build-<perfil>/`, que esa regla no cubre. Falta `firmware/build-*/`.
- `.gitignore:42` ignora el `dependencies.lock` del firmware. Sin él, las dependencias transitivas de ESP-DL quedan sueltas aunque `idf_component.yml` tenga versiones fijas.
- `GET /api/v1/personas/{persona_id}/consentimiento` (`specs/contratos/openapi.yaml:176`) responde 404 tanto si la persona no existe como si no tiene consentimiento vigente. No hay historial de consentimientos ni `aceptado_en` para uno firmado en papel antes de registrarlo.
- `specs/arquitectura.md:39` dice «primera entrada del día»; debe decir «primera entrada permitida» (R5). `specs/modelo-datos.md` no menciona `asistencia.salida`.
- `specs/contratos/mcp-agente.md:121`: `desconocidos_recientes.ultimos` usa `AAAA-MM-DD HH:MM` y la regla general dice `HH:MM`. `llegadas_tarde` no tiene valores por defecto; propongo `hoy`.
- La versión del firmware tiene dos formatos: `tinyml-esp32s3_eye-1.0.0` en la cabecera `X-AccesIA-Firmware` y `1.0.0` en `EstadoCamara`. Falta decir que el simulador no envía `rssi` ni `psram_kb`.
- R6 (`specs/reglas.md:98`) no dice si el borde de la ventana cuenta; R4 sí lo dice («menos de»). Agregar el caso `R6 · borde` con desconocidos en 0, 30 y 60 s.
- La rama `todos/contratos-v1` de la tarea 00 no usa un frente de `CLAUDE.md` (`a`, `b` o `c`).

## 2. Huecos que frenan el Día 1

### 2.1 Proteger `main` en un repo privado · Alta · todo el equipo · decisión del equipo
- Dónde: `tareas/dia-1/00-todos-acordar-contratos.md:54-55` (§ Repositorio) y C4.
- Problema: con GitHub Free, la protección de ramas y los rulesets solo funcionan en repos públicos. El C4 de la tarea 00 no se puede cumplir con un repo privado de una cuenta gratuita.
- Propuesta: que el dueño active GitHub Pro con el Student Developer Pack antes de crear el repo, o hacerlo público: no lleva claves ni fotos.

### 2.2 «Pruebas en verde» sin CI hasta el Día 4 · Media · todo el equipo
- Dónde: `CLAUDE.md` § Reglas de trabajo; `specs/requisitos.md:143` (RNF-06 · C3).
- Problema: sin un workflow, entre el Día 1 y el Día 3 nadie puede exigir pruebas en verde para fusionar un PR.
- Propuesta: un workflow mínimo desde el Día 1: pytest del servidor, `npm run build` y Vitest de la web. La compilación del firmware queda para el Día 4.

### 2.3 La fórmula del recorte no está escrita · Alta · frentes A y B
- Dónde: `specs/contratos/api-dispositivo.md:27` (§ Petición); tarea A, C4.
- Problema: «25 % de margen por cada lado» no dice de qué medida sale el 25 %, si el recorte es cuadrado ni qué significa «la cara más grande». El firmware y el simulador tienen que pasar las mismas pruebas (RF-01 · C6), así que necesitan la misma fórmula.
- Propuesta: escribirla en el contrato: `x0 = x − 0,25·w`, `y0 = y − 0,25·h`, tamaño `1,5·w × 1,5·h`, ajustado a los bordes del cuadro. «Más grande» es la de mayor área. Incluir dos ejemplos numéricos, uno de ellos en el borde.

### 2.4 El SQL del contrato no entra en la imagen Docker · Alta · frente B
- Dónde: `tareas/dia-1/B-cristhian-compose-y-base.md:32` (migración) y `:35` (Dockerfile).
- Problema: la migración debe ejecutar `specs/contratos/base-de-datos.sql` tal cual. Si el contexto de construcción es `servidor/`, ese archivo no queda dentro de la imagen. Lo mismo pasa con el texto del consentimiento, que sirve `GET /api/v1/consentimiento/texto`, y más adelante con la web compilada.
- Propuesta: construir con la raíz del repo como contexto y un `.dockerignore` que deje fuera `datos/`, `kit/` y `node_modules/`.

### 2.5 Las pruebas del firmware en Windows · Media · frente A
- Dónde: `tareas/dia-1/A-julian-esp-idf-y-deteccion.md:45` (§ Hacer, punto 3).
- Problema: la tarea ofrece el target `linux` de ESP-IDF, pero ese target solo funciona en Linux y macOS. La instalación de ESP-IDF tampoco trae un compilador para el PC.
- Propuesta: CMake con doctest o Unity, compilado con Visual Studio Build Tools o dentro de WSL. En GitHub Actions (Día 4) sí se puede usar el target `linux`.

### 2.6 La versión de ESP-DL · Media · frente A
- Dónde: `tareas/dia-1/A-julian-esp-idf-y-deteccion.md:22-23` (§ Antes de empezar).
- Problema: la tarea pide ESP-IDF 5.4 y «la versión vigente» de `esp-dl`. Las versiones nuevas de `esp-dl` y `human_face_detect` pueden pedir un ESP-IDF más nuevo.
- Propuesta: fijar en `idf_component.yml` la última versión de `human_face_detect` compatible con 5.4, o subir ESP-IDF a la versión que pida, y anotarla en la bitácora.

### 2.7 Lo que falta en el plan para el Día 2 · Media · frentes B y C
- Dónde: `specs/plan.md:32-35` (§ Días).
- Nadie tiene asignados los endpoints de sesión, personas, consentimiento, horarios y cámaras, ni la creación del primer administrador con `ADMIN_CORREO`. La tarea C del Día 2 los necesita, y el Día 2 de B solo tiene reconocimiento, R1 a R4, R7 y R9.
- La pantalla Cámaras (RF-09 · C2, RF-10) no está en ningún día, y el Hito 1 necesita una cámara con token. Hace falta un comando del servidor como `crear-camara` o programar la pantalla.
- El comando `semilla agente` de la evaluación del agente (`specs/contratos/mcp-agente.md:150`) tampoco tiene día.

## 3. Riesgos técnicos

### 3.1 El hardware se ve por primera vez en clase · Alta · frente A · decisión del equipo
- Dónde: `CLAUDE.md` § Hardware que todavía no tenemos; `specs/README.md:44` (P-02).
- Problema: ningún binario se habrá probado en una placa real. Un error de pines, de PSRAM o del sensor aparece frente al docente.
- Propuesta: conseguir ya una placa barata de uno de los perfiles (XIAO ESP32S3 Sense o Freenove) para probar antes. Compilar `diagnostico` con `CONFIG_SPIRAM_IGNORE_NOTFOUND=y` para que arranque en cualquier placa.

### 3.2 Umbral y nitidez calibrados con la webcam · Media · frentes A y B
- Dónde: `specs/reglas.md` § R1 (línea 16) y § R7 (línea 118); `specs/requisitos.md` RNF-07.
- Problema: el umbral 0,363 viene de LFW, con caras de buena calidad. Los recortes del ESP32-S3 salen de un cuadro de 320 × 240, con caras de 80 a 120 px que se agrandan a 112 × 112. Eso da menos similitud entre muestras de la misma persona y menos nitidez. Si se inscribe con el simulador y se reconoce con la placa, el reconocimiento falla más.
- Propuesta: un modo del simulador «como la cámara» que reduzca a 320 × 240 y comprima en JPEG 80 antes de detectar. En clase, inscribir con la misma cámara que reconoce y recalibrar `NITIDEZ_MIN` con los valores de `calidad`.

### 3.3 `CARA_MIN_PX` se mide dos veces · Media · frentes A y B
- Dónde: `specs/contratos/api-dispositivo.md:28`; `specs/reglas.md:117` (R7, paso 3).
- Problema: la cámara mide la caja de ESP-DL en el cuadro y el servidor mide la de YuNet en el recorte. Las dos cajas no miden igual, y una cara de unos 80 px puede salir `descartado` una y otra vez.
- Propuesta: decidir un margen entre las dos medidas y escribir su caso de prueba.

### 3.4 Respuestas 429 por la red · Media · frentes A y B
- Dónde: `specs/contratos/api-dispositivo.md:133` (§ Errores, 429).
- Problema: si la cámara envía cada 1,0 s exactos, el retraso de la red puede juntar dos recortes y el servidor responde 429.
- Propuesta: que la cámara cuente el segundo desde que recibe la respuesta, no desde que envía.

### 3.5 Un solo proceso del servidor · Media · frente B
- Dónde: `specs/reglas.md:100` (R6); `specs/arquitectura.md` § Servicios de Docker Compose.
- Problema: la hora de la última alerta de R6, el límite del 429 y la conexión MQTT viven en memoria. Con varios workers de Uvicorn, cada uno cuenta por su lado, y el descubrimiento y el resumen se publican repetidos.
- Propuesta: escribir en `specs/arquitectura.md` que el servidor corre con un solo worker.

### 3.6 El agente con modelos pequeños · Media · frentes B y C
- Dónde: `specs/decisiones.md:23` (D-06); `specs/requisitos.md:74` (RF-08 · C3) y `:126` (RNF-03 · C3).
- Problema: `qwen2.5:1.5b` y `qwen2.5:3b` fallan seguido al llamar herramientas. En una Raspberry, la respuesta puede pasar de 15 s solo procesando las instrucciones y las herramientas.
- Propuesta: medir las 10 preguntas el Día 3 en el portátil. Si no llega a 9 de 10, probar un modelo más reciente de tamaño parecido y actualizar D-06.

### 3.7 Inscribir a otra persona sin querer · Media · frente B · decisión del equipo
- Dónde: `specs/reglas.md:119` (R7) y `:148` (R9).
- Problema: mientras la inscripción está activa, cualquier cara válida de esa cámara se guarda como de la persona inscrita. Si alguien pasa por delante, su cara queda como la de Ana y después entra como Ana. R7 solo compara con las otras personas inscritas.
- Propuesta: agregar a R7 un paso 6: «se parece a las muestras ya aceptadas en esta inscripción».

### 3.8 Windows: puertos reservados y scripts con tildes · Media · todo el equipo
- Dónde: `CLAUDE.md` § Convenciones; `.editorconfig:24` (sección `*.{ps1,bat}`).
- Hyper-V y WSL reservan rangos de puertos al azar, y pueden incluir 5434, 8000 o 1883. Documentar `netsh interface ipv4 show excludedportrange protocol=tcp` en `infra/README.md`.
- Los `.ps1` se guardan en UTF-8 sin BOM. Windows PowerShell 5.1, el que abre VS Code por defecto, los lee como ANSI: las tildes salen dañadas y una raya (–) puede romper el script. Usar `charset = utf-8-bom` para `*.ps1`.

### 3.9 Cuatro detalles de la tarea B · Media · frente B
- Dónde: `tareas/dia-1/B-cristhian-compose-y-base.md` § Hacer; `specs/arquitectura.md:89` (`ADMIN_CORREO`).
- PostgreSQL 18 cambió dónde guarda los datos: el volumen se monta en `/var/lib/postgresql`, no en `/var/lib/postgresql/data` como en versiones anteriores.
- Mosquitto 2 sin un `listener 1883` explícito solo escucha dentro del contenedor.
- `ADMIN_CORREO=admin@accesia.local`: si el correo se valida con `EmailStr` de Pydantic, se rechaza el dominio reservado `.local` y el administrador no puede entrar. Usar otro dominio de ejemplo.
- Agregar el paquete `tzdata` para que `America/Bogota` no dependa de la imagen base.

### 3.10 Skills de terceros sin versión fija · Baja · frente C
- Dónde: `tareas/dia-1/C-jhon-skills-y-web.md` § Skills de frontend.
- Problema: el script trae la última versión de cuatro repos ajenos, y Claude Code sigue sus instrucciones. Cada integrante puede tener una versión distinta, y un cambio en esos repos entra sin revisión.
- Propuesta: fijar el commit de cada repo dentro del script, no solo anotarlo después en `VERSIONES.txt`.

### 3.11 Para más adelante · Baja · frentes A, B y C
- El hotspot de la Raspberry debe ir en 2,4 GHz (`band bg` en NetworkManager): el ESP32-S3 no usa 5 GHz.
- Las versiones recientes del SDK `mcp` pueden rechazar el encabezado `Host: mcp:8001`. Revisarlo al montar el servicio el Día 3.
- Si alguien edita una automatización desde la interfaz de Home Assistant, `automations.yaml` se reescribe y pierde el encabezado y los comentarios.
