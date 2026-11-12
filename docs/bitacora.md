<!--
Nombre: bitacora.md
Descripción: Bitácora de AccesIA: qué se hizo, quién, cómo (incluido el método con IA) y qué quedó pendiente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.8
-->

# Bitácora

Una entrada por tarea terminada, la más reciente arriba. Aquí se cuenta el método con IA; los commits y los PR no lo mencionan.

## Plantilla

```markdown
## AAAA-MM-DD · Día N · Tarea
- Quién:
- Qué: lo que quedó funcionando.
- Cómo: qué se le pidió a Claude Code, qué se revisó o corrigió a mano y qué decisiones se tomaron.
- Pruebas: cuáles corrieron y su resultado.
- Cambios de contrato o de specs: cuáles y por qué (o «ninguno»).
- Pendiente:
```

## 2026-11-12 · Día 2 · Hardware real: specs de la XIAO ESP32-C6 (D-21)

- Quién: el frente A, con los contratos que son del frente B.
- Qué:
  - En clase entregaron una Seeed Studio XIAO ESP32-C6 (4 MB de flash, sin PSRAM ni interfaz de cámara) y una Raspberry Pi 5 con Home Assistant OS. El módulo de cámara llega la próxima clase.
  - D-21 nueva, con una tabla de lo que cambia en D-01, D-02, D-04, D-05, D-06, D-08, D-09, D-10, D-16, D-17, D-18 y D-19.
  - `mqtt.md` 1.2, que solo agrega:
    - el tema `accesia/{codigo}/ambiente`;
    - el descubrimiento de los dos sensores, publicado por la placa;
    - tres líneas de la ACL;
    - `sensor` y `antena` en `EstadoCamara`;
    - el broker de la demo en el portátil.
  - `arquitectura.md` 1.4:
    - la placa del C6, con sus pines, su consola y su comportamiento;
    - el flujo de temperatura y humedad;
    - el escenario 2 como despliegue y la red del hotspot;
    - qué hacer según el módulo de cámara que llegue;
    - el S3 como referencia.
  - `requisitos.md` 1.3: RF-14 nuevo, y cambios en RF-01, RF-07 · C1, RF-11 · C2, RNF-04 · C2 y RNF-06 · C3.
  - Otros archivos:
    - `plan.md` 1.5;
    - `enunciado.md` 1.2, con una nota aparte que no toca el texto del docente;
    - `specs/README.md` 1.2, con P-02 resuelto y P-03 nuevo;
    - `contratos/README.md` 1.4;
    - la guía del día de clase 1.2;
    - `CLAUDE.md` 1.2.
- Cómo:
  - Claude Code propuso el plan del C6 y el equipo lo aprobó con seis decisiones:
    - el broker en el portátil;
    - el sensor cada 30 s, con `null` tras 3 fallas y DHT22 por defecto;
    - el nivel activo en el comando `puerta`, con GPIO15 en bajo en el C6;
    - las specs primero, en una rama `b/`;
    - `esp-idf-lib/dht` 1.2.0 fija;
    - `firmware.yml` adelantado.
  - El equipo hizo dos ajustes: la red de la demo es el hotspot de Windows del portátil en 2,4 GHz, y el enunciado lleva una nota aparte.
  - Antes de escribir se comprobó:
    - ESP-IDF 5.4.4 ya compila para `esp32c6` sin reinstalar nada: el ejemplo `hello_world` tardó 119 s.
    - Los pines coinciden con la wiki de Seeed: GPIO3 y GPIO14 para la antena, el LED en GPIO15, D2 = GPIO2 y sin PSRAM. La wiki no dice en qué nivel enciende el LED.
    - `esp-idf-lib/dht` 1.2.0 declara soporte para `esp32c6`. La 1.2.1 y la 1.2.2 salieron el 11 y el 12 de noviembre, sin targets declarados.
    - El manual de `mosquitto.conf` exige que `%c` ocupe un nivel entero del tema. Por eso el nodo del descubrimiento de la placa es el código.
    - ESP-DL 3.3 declara soporte para `esp32c6`, pero `human_face_detect` solo trae modelos para el S3 y el P4.
- Pruebas: no hay código. La CI del PR corre la web y el servidor. La prueba de la ACL del servidor no lee `mqtt.md`, así que no cambia.
- Cambios de contrato o de specs: `mqtt.md` 1.2, que solo agrega. No se tocan `openapi.yaml` ni `api-dispositivo.md`.
- Pendiente de infra (frentes B y C):
  - `infra/mosquitto/acl`: las tres líneas de `mqtt.md` 1.2, con sus casos en `test_mqtt_acl.py` (`contrato MQTT · acl`). Sin eso, la placa no puede publicar `ambiente` ni su descubrimiento.
  - Firewall de Windows en la red del hotspot: abrir el 1883 (MQTT), y también el 8001 (`mcp`) y el 11434 (`ollama`), que usa Home Assistant OS desde la Pi.
  - El hotspot de Windows del portátil, en 2,4 GHz y con el nombre `AccesIA`.
  - `compose.escenario2.yaml` (Día 4 de C), que pasa a ser el despliegue de la demo.
  - Home Assistant OS: la integración MQTT apunta a `192.168.137.1:1883` con el usuario `homeassistant`, y la copia de seguridad lleva `automatizaciones_accesia.yaml`.
  - Servidor: el `model` del dispositivo pasa a «XIAO ESP32-C6».
  - El kit y `verificar.sh`: el binario del C6 y la comprobación de las entidades de ambiente.
- Otros pendientes:
  - El firmware del C6, en `a/firmware-c6`, después de este PR.
  - P-03: qué módulo de cámara llega.
  - Los diagramas de `docs/diagramas/` todavía muestran el ESP32-S3 y Home Assistant en contenedor. Se regeneran con Archify, no a mano.

## 2026-11-12 · Día 2 · Tarea B1 · Sesión y API de administración

- Quién: el frente B.
- Qué:
  - Contrato de la API 1.3: el código `metodo_no_permitido` para el 405, que conserva la cabecera `Allow`, y el campo `Dispositivo.inscripcion_activa`. Los tipos de la web se regeneraron con `npm run tipos`.
  - Sesión de la web: `POST`, `GET` y `DELETE /api/v1/sesion`. La cookie `accesia_sesion` va firmada con `SESION_SECRETO`, con `HttpOnly`, `SameSite=Strict` y `Path=/`, y dura 8 horas desde el último uso. Las claves se guardan con Argon2id. Al arrancar, el servidor crea el primer administrador («Administrador») con `ADMIN_CORREO` y `ADMIN_CLAVE_INICIAL`; sin `SESION_SECRETO` no arranca.
  - API de personas, consentimiento, horarios por bloques y cámaras, con los códigos de error del contrato.
    - El texto del consentimiento se lee de `specs/consentimiento.md`, que la imagen ahora copia.
    - Revocar borra las huellas y cancela la inscripción activa en la misma transacción.
    - Listar o ver cámaras vence las inscripciones que ya pasaron su hora y muestra `modo` e `inscripcion_activa`. La función queda lista para B2.
  - Comando `accesia crear-camara`, que valida como la API y muestra el token una sola vez.
- Cómo:
  - Claude Code trabajó en un worktree aparte (`AccesIA-b1`), con `infra/.env` y las claves de MQTT copiadas, porque otra sesión seguía la tarea A del Día 1 en la carpeta principal. Propuso el plan y el equipo lo aprobó con estas decisiones: nombre «Administrador», sesión de 8 horas, `SESION_SECRETO` obligatoria, argon2-cffi, itsdangerous y email-validator, `terminada` igual a `vence` en una inscripción vencida, PR en borrador después del contrato y Compose levantado desde el worktree.
  - Un cambio frente al plan: la sesión no usa el `SessionMiddleware` de Starlette, sino una dependencia con la misma cookie firmada con itsdangerous. El middleware necesita la clave al crear la app, es decir al importarla, y eso obligaba a tener `DATABASE_URL` incluso en las pruebas que no usan la base. Para el contrato y para la web no cambia nada.
  - Cada petición usa una transacción, con `Depends(..., scope="function")` de FastAPI: se confirma antes de enviar la respuesta, así quien recibe un 201 ya puede leer lo guardado.
  - El equipo pidió que las pruebas que esperan un error de la base corran dentro de un savepoint. Las pruebas de la API usan la transacción de la prueba y cada petición corre en su savepoint, lo mismo que `join_transaction_mode="create_savepoint"`. Además, las consultas que pueden chocar con una restricción abren otro.
  - Se comprobó rompiendo el código a propósito:
    - sin los dos savepoints, la prueba del 409 falla con `InFailedSqlTransaction`; con cualquiera de los dos, pasa;
    - con la cookie en `SameSite=Lax`, sin vencer las inscripciones o sin cancelar la inscripción al revocar, falló cada vez la prueba que correspondía.
  - Docker Desktop se cerró durante la tarea, y las pruebas fallaban con `CreateFile`. Se volvió a abrir; el README del servidor lo explica.
- Decisiones donde el contrato no decía nada (se copió el simulacro de la web):
  - personas ordenadas por nombre con la colación española `es-x-icu`;
  - un horario que no existe da 422 `validacion`, y un `PATCH` vacío también;
  - un id que no es un uuid da 404;
  - `DELETE /api/v1/sesion` responde 204 aunque no haya sesión;
  - con medio web, `aceptado_en` se ignora y vale la hora del registro;
  - registrar o revocar el consentimiento actualiza `actualizada` de la persona.
- Otras decisiones:
  - En línea es «un contacto en los últimos 2 minutos» hasta que llegue MQTT, y `estado` es `null`.
  - Revocar primero vence las inscripciones que ya pasaron su hora y después cancela la activa.
  - El servidor toma la hora de `accesia.tiempo.ahora()` para todo lo que guarda y compara, para que las pruebas la controlen.
- Pruebas:
  - `uv run pytest`: 164 en verde, entre ellas las 24 del Día 1, la nueva del 405 y 139 de B1, con su resumen por marca. Ruff (`F`, `E9` y `B`) sin observaciones.
  - Web: `npm run build` y `npm test` (68) en verde; `npm run tipos` sin cambios. `openapi-spec-validator`: `openapi.yaml` 1.3 OK.
  - Compose con la imagen nueva:
    - salud OK, 405 `metodo_no_permitido` y 401 `sin_sesion`;
    - el administrador de `infra/.env` quedó creado con Argon2id;
    - un script, sin mostrar las claves, recorrió sesión, horarios, persona, documento repetido, búsqueda sin tildes, consentimiento, revocación, borrado y cierre de sesión;
    - `crear-camara` en el contenedor: token de 43 caracteres con su SHA-256 igual al guardado; rechaza el código repetido y `servidor`; en PowerShell las tildes se ven bien. La cámara de prueba se borró.
  - Web real con `npm run dev` y Playwright, con un script aparte que lee las credenciales de `infra/.env` sin mostrarlas: entra, crea una persona con «Clase IA», «Inscribir» está deshabilitado, registra el consentimiento, «Inscribir» se habilita, el historial muestra «Versión 1.0 · En la web… lo registró Administrador» y la sesión sigue al recargar. La persona de prueba se borró. La primera corrida falló esperando el aviso de consentimiento registrado; las tres siguientes pasaron y no se encontró la causa.
  - La CI del PR corre las mismas pruebas; el PR se fusiona solo con `servidor.yml` y `web.yml` en verde.
- Cambios de contrato o de specs: `openapi.yaml` 1.3, `contratos/README.md` 1.3 y su registro en `decisiones.md` 1.5. `arquitectura.md` 1.3 anota la duración de la sesión, que sin `SESION_SECRETO` no arranca y el nombre y la clave mínima del primer administrador. `CLAUDE.md`, `servidor/README.md` e `infra/README.md` suman `crear-camara`.
- Pendiente:
  - Los endpoints de rostros (RF-12 · C1) y `GET /api/v1/configuracion` siguen sin tarea: se asignan el Día 3.
  - `en_linea` y `estado` de las cámaras se completan con MQTT el Día 3.
  - El registro del contenedor no muestra los avisos de nivel INFO del servidor (por ejemplo, que creó el primer administrador): uvicorn no configura ese registro. Los de nivel WARNING y ERROR sí salen.
  - argparse escribe en inglés sus propios mensajes (`usage`, `the following arguments are required`).
  - Starlette sigue avisando que `TestClient` con httpx está en desuso.

## 2026-11-12 · Día 2 · Tareas del Día 2

- Quién: el frente B, para todo el equipo.
- Qué: las tareas del Día 2 en `tareas/dia-2/`, con la plantilla de `tareas/README.md`:
  - `00-todos-orden-e-hito-1.md`: orden entre tareas, acuerdos para no pisarse y guion del Hito 1, con sus criterios y qué revisar si algo falla.
  - `A-julian-simulador.md`: simulador con YuNet, la fórmula y los casos del recorte, el envío de `api-dispositivo.md`, el modo «como la cámara» (320 × 240 y JPEG 80) y el modo carpeta. La puerta por MQTT queda para el Día 3.
  - `B1-cristhian-sesion-y-api.md`: sesión y primer administrador; API de personas, consentimiento, horarios por bloques y cámaras; comando `crear-camara`; contrato de la API 1.3 con `metodo_no_permitido` y el campo `inscripcion_activa` de las cámaras.
  - `B2-cristhian-reconocimiento-e-inscripcion.md`: reconocimiento con YuNet + SFace + pgvector, R1 a R4, R7 e inscripción (R9).
  - `C-jhon-inscripcion-y-camaras.md`: Personas y consentimiento contra la API real, y pantallas Inscripción (barra «Muestra 3 de 5», y ver o cancelar la inscripción activa ante un 409) y Cámaras.
- Cómo: se le pidió a Claude Code escribir las tareas sin escribir código, desde un worktree aparte, porque otra sesión trabajaba la tarea A del Día 1 en la carpeta principal. Leyó el plan, las specs, los contratos vigentes, la bitácora, la revisión de los contratos y el código del Día 1. Del Día 1 se llevaron a las tareas:
  - La CI de la web falla si `esquema.d.ts` no coincide con `openapi.yaml`: B1 regenera los tipos en el mismo PR en que cambia el contrato.
  - Cada prueba del servidor lleva su marca: las tareas nombran las marcas nuevas.
  - Donde el contrato no dice nada, el servidor responde como el simulacro de la web: orden por nombre, horario inexistente 422.
  - Los espacios duros de la web van como ` `.
  - El 405 respondía `no_encontrado`; B1 propone `metodo_no_permitido`.
- Cambio pedido en la revisión: el contrato 1.3 de B1 también agrega a `Dispositivo` el campo `inscripcion_activa` (`InscripcionCorta` o `null`), para que la web encuentre la inscripción activa de una cámara si pierde su id. En C, ante un 409 `inscripcion_activa`, la pantalla Inscripción ofrece ver o cancelar esa inscripción, y Cámaras la muestra.
- Decisiones menores al escribir, para revisarlas en el PR:
  - Ramas: `a/simulador`, `b/sesion-y-api`, `b/reconocimiento`, `c/inscripcion-y-camaras` y `b/hito-1`, esta solo para el resultado del hito.
  - Orden si una sola persona hace varias: B1, B2, A y C.
  - Los ONNX no se suben: en el PC quedan en `datos/modelos/` (Git y Docker ya ignoran `datos/`) y la imagen los descarga al construir, con URL de un commit fijo de opencv_zoo y SHA-256. La primera tarea que fije YuNet lo anota en `arquitectura.md` y la otra lo reusa.
  - La CI no tiene caras: las reglas se prueban con la visión reemplazada, y las pruebas con caras reales leen `datos/prueba/` y se saltan si no existe.
  - El token del simulador sale de `TOKEN_CAMARA`, como en el ejemplo de `api-dispositivo.md`.
  - Forma de los comandos que usa el guion del hito: `accesia crear-camara entrada --nombre Entrada --tipo simulador` y `uv run simulador webcam --codigo entrada --como-camara`.
  - El simulador todavía no entra a GitHub Actions: RNF-06 · C3 suma el frente A el Día 4.
  - Las tareas piden proponer en el plan lo que las specs no dicen: formato de las respuestas esperadas del modo carpeta, cómo llevar una imagen 16:9 a 320 × 240, nombre del primer administrador, duración de la sesión, mensajes de la respuesta, orden de las comprobaciones de `enviarRostro` y qué responder si se abre una inscripción en una cámara inactiva.
- Pruebas: no hay código. Se revisaron a mano las referencias de las tareas: archivos, secciones, criterios RF y RNF, casos de las reglas, códigos de error y operaciones de `openapi.yaml`.
- Cambios de contrato o de specs: ninguno en los contratos (el 1.3 lo hace B1 en su PR). `specs/plan.md` 1.4 tiene una fila por tarea del Día 2, con B dividida en B1 y B2, y `specs/decisiones.md` lo anota en su registro. `tareas/README.md` suma el Día 2.
- Pendiente: asignar el Día 3 a lo que no tiene tarea: los endpoints de rostros (RF-12 · C1) y `GET /api/v1/configuracion`.

## 2026-11-11 · Día 1 · Tarea C · Skills de frontend y web base

- Quién: el frente C.
- Qué:
  - `scripts/preparar-skills.ps1` y `.sh` traen los seis skills de frontend a `.claude/skills/`, cada uno en su commit fijo. También traen la copia local de las reglas de web-design-guidelines (`command.md`, commit `434b7f9` de `vercel-labs/web-interface-guidelines`). Tienen la opción `-Actualizar` (`--actualizar` en Bash), anotan cada commit en `VERSIONES.txt` y no cambian nada si algo falla.
  - `web/` queda con React 19, Vite 8, React Router 8, TanStack Query 5 y `openapi-fetch`, con los tipos generados desde `openapi.yaml`. Tiene el simulacro de la API con MSW 3 y estas pantallas:
    - Inicio de sesión.
    - Personas: búsqueda sin tildes, filtro y paginación guardados en la dirección, y activar o desactivar con «Deshacer».
    - Formulario para crear y editar: el horario se elige de la lista, con el resumen de sus bloques, y avisa antes de salir con cambios sin guardar.
    - Ficha con el consentimiento: texto de la API, aviso de que es opcional, registro en web o en papel, revocación confirmada e historial. «Inscribir» solo se habilita con consentimiento vigente.
    - «Próximamente» en las otras cinco secciones.
  - La CI de la web quedó en `.github/workflows/web.yml`.
- Cómo:
  - Claude Code propuso el plan y la dirección visual. El equipo la aprobó con lucide-react para los íconos y con las reglas de web-design-guidelines fijadas en `434b7f9`. De impeccable se usaron solo sus guías; su ejecutable no se corrió.
  - Skills: se revisó qué trae cada repositorio antes de fijar su commit. El script se probó en PowerShell 5.1 y en Git Bash: los dos dejan los mismos 1.727 archivos, byte a byte. En copias del script se probó `--actualizar` con commits viejos simulados y también una ruta que cambió: avisa dónde quedó la carpeta, sale con código 1 y no toca nada.
  - Errores que aparecieron y se corrigieron:
    - En Bash, `grep -q` dentro de una tubería con `pipefail` daba SIGPIPE en los repositorios grandes. Se cambió a here-strings.
    - En Git Bash, `sed` y `awk` quitan los CR del `.ps1`. La tabla se actualiza con Bash puro.
    - `openapi-typescript` volvía obligatorios los campos con valor por defecto (`activa`, `medio`). Se genera con `--default-non-nullable false`.
    - Se usa TypeScript 5.9, porque `openapi-typescript` 7 pide TypeScript 5.
    - En MSW 3, `onUnhandledRequest` pasó a llamarse `onUnhandledFrame`.
    - El simulacro entraba al paquete de producción. Ahora una constante de compilación (`__SIMULACRO__`) lo saca.
    - Playwright encontró un error real: si el filtro cambiaba mientras la búsqueda esperaba, el filtro se perdía.
    - La prueba de teclado encontró otro: después de entrar, el foco quedaba perdido.
    - Los espacios duros (U+00A0) que escribía la herramienta llegaban al código como caracteres invisibles. Se dejaron como secuencias de escape, que se ven.
  - Revisión visual: Claude Code revisó las capturas de cada pantalla a 1280×720 y 1440×900. Se corrigieron estos problemas:
    - la columna Datos era angosta;
    - salían el punto doble «a. m..» y la hora partida entre «a.» y «m.»;
    - una insignia larga aplastaba el historial;
    - la barra lateral se veía cortada en las capturas de página completa;
    - la tabla tenía subrayados de más.
  - Accesibilidad: revisión con la copia local de `command.md`. Se cambió la paginación a enlaces, se pusieron espacios duros en «10 min», se agregó `autocomplete` y se escribió una prueba automática del contraste AA.
- Decisiones:
  - El script de skills es todo o nada: si un repositorio falla, no se cambia ninguno.
  - El simulacro vive en la memoria de la pestaña, con datos ficticios. Sus credenciales de prueba (`admin@example.com` y `simulacro`) solo existen en él.
  - «Inscribir» es un botón y no un enlace, porque debe poder deshabilitarse (RF-02 · C4).
  - Los títulos y botones van en mayúscula solo en la primera palabra, como se escribe en español, aunque web-design-guidelines pide *Title Case*.
  - Los tokens, los componentes y el skill que apoya cada decisión quedan en `web/DESIGN.md`.
- Pruebas:
  - `npm test` (Vitest): 68 en verde, entre fechas en hora de Colombia, validaciones, horarios, texto, el simulacro contra el contrato y el contraste AA.
  - `npm run e2e` (Playwright con el simulacro): 9 en verde, incluidas la prueba de teclado y las capturas.
  - `npm run build` en verde, sin el simulacro en el paquete. `npm run tipos` regenera los tipos sin cambios.
  - Script de skills: cinco corridas manuales. Instalación normal y `--actualizar` en PowerShell 5.1 y en Bash, más una ruta que cambió.
- Cambios de contrato o de specs: ninguno en los contratos. Antes de empezar, D-11 pasó a seis skills, y se actualizaron la tarea C, `CLAUDE.md` (sección Web) y el extra de `plan.md`. Al terminar, `CLAUDE.md` sumó los comandos de los skills y de la web.
- Pendiente:
  - Ver `web.yml` en verde en el PR (C7).
  - Llevar Playwright a la CI el Día 4.
  - Conectar la web con el servidor real cuando la tarea B del Día 2 tenga sesión y personas.
  - `public/mockServiceWorker.js` también se copia a `dist/`. No se registra sin simulacro, pero se puede excluir cuando el servidor sirva la web.

## 2026-11-11 · Día 1 · Tarea B · Docker Compose, base de datos y esqueleto del servidor

- Quién: el frente B.
- Qué: con `docker compose -f infra/compose.yaml up -d --build` quedan sanos `postgres` (PostgreSQL 18 + pgvector), `mosquitto` y `servidor`, con el esquema del contrato 1.2 migrado y `/api/v1/salud` respondiendo. También quedaron los scripts `generar-env` y `crear-claves-mqtt` (`.ps1` con BOM y `.sh`), 24 pruebas con pytest y la CI en `.github/workflows/servidor.yml`.
- Cómo: se le pidió a Claude Code un plan corto, ajustado a los horarios por bloques (D-20), y el equipo lo aprobó con un cambio: la ACL de Mosquitto se comprueba con una prueba automática (`contrato MQTT · acl`) y no con un paso manual. Claude Code instaló uv con winget, escribió el código y lo verificó. Para confirmar que las pruebas de la ACL no pasan siempre, rompió la ACL a propósito tres veces: quitó la línea `deny`, abrió el estado de todas las cámaras y permitió el acceso anónimo. Cada vez falló justo la prueba que correspondía, y después dejó los archivos como estaban.
- Decisiones:
  - La migración ejecuta el SQL con el cursor de psycopg, sin parámetros, dentro de la transacción de Alembic. La imagen copia el SQL a la misma ruta relativa que en el repositorio, y la migración lo busca subiendo carpetas. Si el usuario `agente` ya existe, le actualiza la clave.
  - El 405 se responde con `no_encontrado`, porque el contrato no tiene un código para «método no permitido».
  - FastAPI no publica su propio OpenAPI: el contrato es `specs/contratos/openapi.yaml`.
  - El paquete arranca en la versión `0.1.0`. `config.py` solo exige `DATABASE_URL`; las reglas tienen los valores de `arquitectura.md` por defecto.
  - Cada prueba lleva `@pytest.mark.marca("…")`: pytest no corre si alguna no la tiene, y al final muestra un resumen por marca.
  - El healthcheck de Mosquitto entra con el usuario `servidor` usando `mosquitto_sub -E`.
  - `mosquitto_passwd -c` no sobrescribe un archivo existente, así que los scripts borran `passwd` antes de crearlo. Ese error salió al correrlos dos veces.
- Pruebas:
  - `uv run pytest`: 24 en verde. Por marca: esquema 1, vector 1, horarios 5, RF-08 · C4 7, salud 1, error 3 y ACL de MQTT 6.
  - Compose: los tres servicios sanos; PostgreSQL publicado solo en `127.0.0.1:5434`, con los datos en `/var/lib/postgresql/18/docker`; migración `0001` aplicada una sola vez, incluso tras reiniciar.
  - El usuario `agente` entra con la clave de `infra/.env`.
  - Los cuatro scripts funcionan y se pueden correr varias veces.
  - La imagen también compila para `linux/arm64`.
- Cambios de contrato o de specs: ninguno. `CLAUDE.md` tiene ahora la sección «Comandos».
- Pendiente:
  - Ver la CI en verde en el PR (C7).
  - Starlette avisa que `TestClient` con `httpx` está en desuso y pide `httpx2`; la tarea nombra `httpx`, así que se dejó así.
  - Fijar las versiones exactas de las imágenes el Día 4.

## 2026-11-11 · Día 1 · Horarios por bloques (D-20, contratos 1.2)

- Quién: el frente B.
- Qué: cada horario tiene ahora un nombre y bloques por día (día, hora de inicio y tolerancia), uno por día como máximo. Los contratos `base-de-datos.sql`, `openapi.yaml` y `mcp-agente.md` pasan a 1.2. También cambiaron D-20, R5 (con tres casos nuevos), RF-06 · C3, RF-09 · C2, el requisito nuevo RF-13, el modelo de datos, el plan (Día 2 de B y Día 3 de C), las tareas B y C del Día 1 y `web/README.md`.
- Cómo: el equipo decidió D-20 y Claude Code aplicó el cambio en la rama `b/horarios-1-2`, sin escribir código. Antes de seguir con la tarea B, Claude Code verificó el contrato.
- Decisiones menores al aplicar:
  - `horario_bloque` tiene como clave primaria `(horario_id, dia)`, sin un id propio, porque la API reemplaza la lista completa de bloques.
  - El mínimo de un bloque lo valida la API, no la base.
  - En la API, cada bloque pide su tolerancia; en la base, la tolerancia por defecto sigue siendo 10.
  - Un día repetido responde 422 `validacion`, y la lista admite como máximo 7 bloques.
  - El «por qué» de D-20 sale del ejemplo de lunes a las 07:00 y miércoles a las 18:00.
  - El horario de los casos nuevos de R5 se llama «Lunes y miércoles», con fechas de la semana del lunes 16 de noviembre de 2026.
  - En la tarea C, el horario de la persona se elige de la lista de horarios.
- Pruebas: `openapi.yaml` 1.2 pasa `openapi-spec-validator`. `base-de-datos.sql` 1.2 cargó en PostgreSQL 18.6 con pgvector, y pasaron las comprobaciones de los bloques, de la vista del agente y de los tres casos nuevos de R5. Se revisaron las referencias cruzadas.
- Cambios de contrato o de specs: los tres contratos pasan a 1.2 (registro de cambios en `specs/decisiones.md`). El esquema `Horario` cambia de campos, así que rompe la 1.1. Según `specs/contratos/README.md` eso sería 2.0, pero se dejó en 1.2 porque todavía no hay código que lo use.
- Pendiente: el plan de la tarea B, ajustado a los bloques; las preguntas 1 a 5 y 11 de la tarea 00.

## 2026-11-11 · Día 1 · AccesIA como raíz del repositorio

- Quién: el frente B.
- Qué: AccesIA quedó como raíz de su propio repositorio. Antes, el repositorio git estaba en la carpeta de arriba (`Inteligencia artificial/`) y el primer commit incluía otro proyecto de la materia (entrenamiento distribuido con TensorFlow). En GitHub, `main` se reemplazó con un push forzado y ahora solo tiene AccesIA.
- Cómo: lo detectó Claude Code al revisar las referencias cruzadas, porque GitHub solo corre los workflows de `.github/workflows/` en la raíz del repositorio. Propuso tres opciones y se eligió reescribir el mismo repositorio de GitHub, que era privado, solo tenía `main` y no tenía otros colaboradores. Pasos: respaldo con `git bundle` en `Universidad/respaldo-git-inteligencia-artificial-2026-11-11.bundle`; `git subtree split --prefix=AccesIA` de `main` y de `b/contratos-v1-1`; repositorio nuevo dentro de `AccesIA/`; `git push --force-with-lease` de `main` y push de `b/contratos-v1-1`.
- Pruebas: las ramas nuevas tienen el mismo árbol que `AccesIA/` en las viejas, con los mismos autores y fechas. En GitHub, `main` tiene la raíz de AccesIA y nada del otro proyecto, y el árbol de `b/contratos-v1-1` es igual al local.
- Cambios de contrato o de specs: ninguno. Los commits cambiaron de identificador: `4c3cca5` pasó a `cd480c4` y `915b0c2` a `8075dc0`.
- Pendiente: renombrar a `.git-viejo` el `.git` de la carpeta de arriba (falló porque VS Code estaba abierto). El proyecto de TensorFlow queda sin git; si lo quieren versionado, va en otro repositorio.

## 2026-11-11 · Día 1 · Tarea 00 · Contratos 1.1

- Quién: los tres integrantes acordaron en la tarea 00; el frente B aplicó los cambios en la rama `b/contratos-v1-1`.
- Qué: los acuerdos sobre la revisión de los contratos quedaron en las specs, los cinco contratos (versión 1.1), las tareas del Día 1, la guía del día de clase, `.gitignore` y `.editorconfig`. Se agregó `specs/contratos/casos-recorte.json` con los casos de la fórmula del recorte.
- Cómo: Claude Code hizo primero la revisión, sin cambiar archivos (`docs/revisiones/2026-11-11-revision-contratos-v1.md`). El equipo decidió punto por punto en la tarea 00. Después se le pidió a Claude Code aplicar esos acuerdos sin escribir código; las decisiones menores que tomó al aplicarlos quedan en la lista de abajo para revisarlas en el PR.
- Decisiones menores al aplicar: el código de error nuevo se llama `asistencia_duplicada` y el motivo nuevo de R7, `distinta_de_la_primera`. La asistencia de una persona se consulta en `GET /api/v1/personas/{persona_id}/asistencia`, y una llegada manual no puede tener hora futura. La tolerancia de 0,8 × `CARA_MIN_PX` se aplica al reconocer y al inscribir. En un `permitido` repetido, el mensaje MQTT lleva el `evento_id` original y la hora y la similitud del recorte nuevo. La ACL de `camara` agrega `topic deny accesia/servidor/#`. `EstadoCamara.firmware` usa el texto de la cabecera HTTP y el simulador no envía `perfil`, `rssi`, `psram_kb` ni `libre_kb`. El ejemplo de `ADMIN_CORREO` es `admin@example.com`. Los archivos nuevos se llaman `compose.ollama-portatil.yaml`, `automatizaciones_accesia.yaml`, `firmware.yml` y `compilar-binarios.ps1`. Las opciones del script de skills son `-Actualizar` y `--actualizar`. La fórmula del recorte redondea hacia afuera (piso al inicio y techo al final). También se arregló una descripción mal escrita del esquema `Error` de `openapi.yaml`, que creaba una clave suelta.
- Pruebas: `openapi.yaml` pasa `openapi-spec-validator` (OpenAPI 3.1). `base-de-datos.sql` 1.1 cargó en PostgreSQL 18.6 con pgvector (imagen `pgvector/pgvector:pg18`) y pasaron 11 comprobaciones: el código `servidor` se rechaza, `distinta_de_la_primera` se acepta como motivo, la asistencia guarda origen y autor, solo hay una llegada por día, y el usuario `agente` lee `v_asistencia_agente` (incluidas las llegadas manuales) pero no la tabla `asistencia`. Los dos casos de `casos-recorte.json` cumplen la fórmula. Se revisaron las referencias cruzadas: criterios RF, decisiones D, temas MQTT, variables, enums y columnas de las tablas Markdown.
- Cambios de contrato o de specs: los cinco contratos pasan a 1.1; el detalle está en el registro de cambios de `specs/decisiones.md`. Algunos cambios rompen la 1.0: `GET .../consentimiento` responde `null` en vez de 404 sin consentimiento vigente, las cámaras deben conectarse a MQTT con su código como client id, el 429 se mide con 0,8 s, `FilaAsistencia` pide `origen` y `registrado_por` y `EstadoCamara.firmware` cambia de formato. No afecta a nadie porque todavía no hay código.
- Pendiente: las preguntas 1, 2, 3, 4, 5 y 11 de la tarea 00 (quién consigue una placa antes de la clase). Revisar en el PR las decisiones menores de arriba.

## 2026-11-11 · Antes del Día 1 · Kit base del repositorio

- Quién: Cristhian Sánchez, para todo el equipo.
- Qué: `CLAUDE.md`, specs (enunciado, decisiones, arquitectura, requisitos, reglas, modelo de datos, consentimiento y plan), contratos (API, MQTT, agente y base de datos), tareas del Día 1, esta bitácora, la guía del día de clase y los diagramas.
- Cómo: las specs y los contratos se redactaron con Claude (claude.ai) a partir del levantamiento y del plan del proyecto. El equipo los revisa y los acepta en la tarea 00 del Día 1.
- Pruebas: `openapi.yaml` pasó `openapi-spec-validator`; `base-de-datos.sql` se cargó en un PostgreSQL 16 de prueba (con `vector` y `uuidv7` simulados) y se comprobaron restricciones, vistas, permisos del agente y borrado en cascada.
- Cambios de contrato o de specs: decisiones D-12 a D-19 propuestas.
- Pendiente: P-01 fecha de la clase; P-02 hardware que entregan; cargar el esquema en PostgreSQL 18 con pgvector (tarea B del Día 1).
