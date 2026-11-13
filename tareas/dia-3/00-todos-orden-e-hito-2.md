<!--
Nombre: 00-todos-orden-e-hito-2.md
Descripción: Día 3 para los tres integrantes: el Hito 1 primero, dependencias y orden entre las tareas A1, A2, B1, B2, B3, C1 y C2, reparto entre tres sesiones, el Compose desde la carpeta principal y guion del Hito 2.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Todos · Orden de las tareas e Hito 2

- Responsables: Julián, Cristhian y Jhon
- Rama: cada tarea tiene la suya. El resultado del Hito 2 va en la rama `b/hito-2`, solo con la bitácora y las specs que cambien.
- Lee primero: `specs/plan.md`; `specs/decisiones.md` (D-21 y su tabla de cambios); `specs/arquitectura.md` (Red y despliegue, Firmware); `tareas/README.md` y las siete tareas del Día 3.

## Objetivo

Que las tareas del Día 3 avancen en tres sesiones sin pisarse y que al final del día, con el hardware de D-21, Home Assistant abra la puerta cuando el simulador reconoce a alguien y Assist diga quién llegó tarde (Hito 2). Antes va el Hito 1 del Día 2, que todavía no se ha corrido (ver «Hito 1 primero»). Si un hito no se cumple, se resuelve antes de seguir (`specs/plan.md`).

## Con qué se trabaja (D-21)

- Docker Compose corre en el portátil: servidor, PostgreSQL, Mosquitto, `mcp` y Ollama. Es el escenario 2.
- La red es el hotspot de Windows del portátil, `AccesIA`, en 2,4 GHz. El portátil suele quedar en `192.168.137.1`.
- La Raspberry Pi 5 trae Home Assistant OS y se conecta al broker del portátil con el usuario `homeassistant`.
- La XIAO ESP32-C6 maneja la puerta (el LED de GPIO15) y el sensor de temperatura y humedad, con el firmware del PR #11 (`a/firmware-c6`).
- La cámara sigue siendo el simulador hasta que llegue el módulo (P-03).

## Tareas del Día 3

| Archivo | Responsable | Rama | Depende de |
| --- | --- | --- | --- |
| [A1-julian-puerta-del-simulador.md](A1-julian-puerta-del-simulador.md) | Julián Andrés Silva Morales | `a/puerta-simulador` | Nada del servidor: solo el broker de Compose y `mqtt.md` |
| [A2-julian-camara-de-la-placa.md](A2-julian-camara-de-la-placa.md) | Julián Andrés Silva Morales | `a/camara-placa` | Que llegue el módulo de cámara (P-03); el PR #11 ya está en `main` |
| [B1-cristhian-asistencia-y-consultas.md](B1-cristhian-asistencia-y-consultas.md) | Cristhian Eduardo Sánchez Mosquera | `b/asistencia` | B2 del Día 2 (ya en `main`) |
| [B2-cristhian-mqtt.md](B2-cristhian-mqtt.md) | Cristhian Eduardo Sánchez Mosquera | `b/mqtt` | B1, por la asistencia del evento y el resumen (el PR #11, con la ACL, ya está en `main`) |
| [B3-cristhian-mcp-y-semilla.md](B3-cristhian-mcp-y-semilla.md) | Cristhian Eduardo Sánchez Mosquera | `b/mcp-agente` | B1, por R5 en la semilla |
| [C1-jhon-accesos-asistencia-y-horarios.md](C1-jhon-accesos-asistencia-y-horarios.md) | Jhon Jairo Perdomo Perdomo | `c/accesos-asistencia-horarios` | C del Día 2 fusionada; B1 para probar contra el servidor real (antes, simulacro) |
| [C2-jhon-home-assistant-y-agente.md](C2-jhon-home-assistant-y-agente.md) | Jhon Jairo Perdomo Perdomo | `c/home-assistant` | La Pi 5 y el hotspot para empezar; B2 (entidades y eventos) y B3 (`mcp` y semilla) para terminar. El PR #11, ya en `main`, da la puerta y el ambiente de la placa |

## Qué está en curso al empezar

- El PR #11 ya está en `main`: el firmware de la placa, la ACL 1.1 de MQTT y `firmware.yml`. Nadie más toca `firmware/` ni `infra/mosquitto/acl`.
- La tarea C del Día 2 (`c/inscripcion-y-camaras`) sigue en curso y hace su e2e contra el Compose que hoy corre desde `AccesIA-b2`. Nadie baja ese Compose ni borra ese worktree hasta que esa tarea se fusione.

## Hito 1 primero

- El Hito 1 del Día 2 (`tareas/dia-2/00-todos-orden-e-hito-1.md`) todavía no se ha corrido. Va primero: apenas se fusione la C del Día 2, y antes del Hito 2.
- Para el Hito 1, el Compose pasa a la carpeta principal. Se baja el de `AccesIA-b2` sin `-v`, para conservar los datos, y se levanta desde la carpeta principal, en `main` (ver «Docker Compose» en los acuerdos).
- Las tareas del Día 3 siguen mientras tanto. Durante un hito no se fusiona nada que obligue a reconstruir el Compose.
- Si el Hito 1 no se cumple, se resuelve antes del Hito 2.

## Qué va en paralelo (tres sesiones)

El camino crítico es B: B2 y B3 necesitan B1, y el Hito 2 necesita las tres. Por eso B1 empieza primero.

| Turno | Sesión A | Sesión B | Sesión C |
| --- | --- | --- | --- |
| 1 | A1 | B1 | Termina la C del Día 2 |
| 2 | Hito 1, apenas se fusione la C del Día 2 | Hito 1 | Hito 1 |
| 3 | B3, si la sesión A quedó libre y B1 está en `main` | B2 (con B1 en `main`) | C1 contra el simulacro; contra el servidor real con B1 |
| 4 | A2, si llegó el módulo | B3, si nadie la tomó | C2: empieza por lo que no espera a nadie y termina con B2 y B3 en `main` |
| 5 | Hito 2 | Hito 2 | Hito 2 |

- Van en paralelo sin chocar:
  - A1 con todo lo demás: solo toca `simulador/`.
  - B1 con C1: C1 empieza contra el simulacro.
  - B2 con B3, una vez fusionada B1. Comparten solo `pyproject.toml` y `uv.lock`: el segundo PR trae `main` y vuelve a correr `uv lock`.
  - C2 con todo, en su primera parte: hotspot, firewall, Home Assistant OS, Ollama y los archivos de `homeassistant/`.
- No van en paralelo:
  - el Hito 2 antes del Hito 1;
  - B2 o B3 antes de B1;
  - `compose.escenario2.yaml` de C2 antes de B3, porque publica el servicio `mcp`;
  - A2 sin el módulo.
- Si una misma persona hace varias tareas el mismo día, este orden evita bloqueos: B1, B2, B3, A1, C1, C2 y A2.
- B3 sigue siendo de Cristhian aunque la corra la sesión A: la sesión es solo dónde se ejecuta.

## Acuerdos para no pisarse

- Docker Compose, desde el Hito 1:
  - corre solo desde la carpeta principal (`AccesIA`), que siempre está en `main`. Ninguna sesión lo levanta desde su worktree;
  - quien fusiona un PR que cambia el servidor, la web o la infra hace `git pull` en la carpeta principal y lo reconstruye, avisando a las demás sesiones. Lo levanta con `docker compose -f infra/compose.yaml up -d --build`, y con `-f infra/compose.escenario2.yaml` cuando exista;
  - las pruebas de cada tarea no lo necesitan: el servidor usa testcontainers, la web su simulacro y el simulador sus dobles;
  - una tarea que cambia la infra la revisa antes de fusionar con `docker compose … config` y sus pruebas. El arranque real se comprueba al reconstruir.
- Contratos:
  - Nadie cambia un contrato hoy sin proponerlo antes (`specs/contratos/README.md`).
  - B2 propone en su PR si `EstadoCamara` suma `sensor` y `antena` en `openapi.yaml`, como ya dice `mqtt.md` 1.2. Si se acepta, es la 1.4 (solo agrega), y B2 regenera `web/src/api/esquema.d.ts` con `npm run tipos`.
- Archivos compartidos:
  - `infra/compose.yaml`: B3 suma el servicio `mcp`, y C2 suma `ollama` si Ollama va en Compose. El segundo que fusione trae `main` y conserva los dos servicios.
  - `.env.example` y `arquitectura.md` (Configuración): solo suma variables quien las necesita, y lo anota.
- MQTT:
  - Los temas son los de `mqtt.md` 1.2; nadie inventa temas.
  - La placa y el simulador no pueden usar a la vez el mismo código como client id (`mqtt.md`, Broker). Si la placa maneja la puerta de `entrada`, el simulador envía los recortes de `entrada` sin conectarse a MQTT (A1).
- Datos:
  - Las fotos de prueba siguen en `datos/prueba/`, con su permiso; nunca se suben.
  - La semilla del agente (B3) no se mezcla con personas reales sin que el plan de B3 diga cómo.

## Guion del Hito 2

Qué se demuestra:

- con el hardware de D-21, el simulador reconoce a una persona inscrita;
- el servidor publica el evento y Home Assistant abre la puerta de la placa;
- la llegada queda tarde según su horario, y Assist lo dice;
- los desconocidos generan una notificación.

### Preparación

- El Hito 1 cumplido, y `main` con A1, B1, B2, B3 y C2 (C1 es deseable, no obligatoria). El PR #11 ya está.
- El hotspot de Windows `AccesIA` en 2,4 GHz. El firewall del portátil deja entrar desde `192.168.137.0/24` lo que Home Assistant usa en él: el 1883 (MQTT), el 8001 (MCP) y el 11434 (Ollama). Ollama escucha fuera de localhost (C2). El 8000 se suma cuando la placa envíe recortes.
- La Pi 5 con Home Assistant OS en el hotspot, con lo de C2: integración MQTT con el broker del portátil, Ollama, MCP, el agente «Portería», las automatizaciones y el panel.
- La placa con el firmware del PR #11, en el hotspot, con el código `entrada` y el token de la cámara `entrada`.
- Una persona inscrita en el Hito 1, con consentimiento, y otro integrante sin inscribir, que hará de desconocido.
- Tres terminales de PowerShell en la raíz del repositorio: servidor, web y simulador.

### Pasos

1. Levantar el servidor en el escenario 2, desde la carpeta principal en `main` (terminal 1):

   ```powershell
   docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml up -d --build
   curl.exe http://localhost:8000/api/v1/salud
   ```

   Esperado: `estado` `ok`, con `base` y `mqtt` en `ok`.

2. Home Assistant: el dispositivo «AccesIA Entrada» muestra la puerta, la cámara en línea, la temperatura y la humedad, y «AccesIA Servidor» muestra sus sensores (RF-07 · C1, RF-14 · C4).

3. En la web, la pantalla Horarios: crear el horario «Hito 2» con un bloque hoy, a una hora que ya pasó, con 10 min de tolerancia, y asignárselo a la persona inscrita (RF-13). Sin la pantalla, se usa la API.

4. La persona mira la webcam, con el simulador sin MQTT, porque la placa tiene el código `entrada` (terminal 3):

   ```powershell
   cd simulador
   uv run simulador webcam --codigo entrada --como-camara
   ```

   Esperado:
   - `permitido`;
   - el LED de la placa se enciende 3 s, y la entidad Puerta pasa a abierta y vuelve a cerrada;
   - del recorte a la puerta abierta, menos de 2 s, medido con la hora del registro del servidor y el registro de Home Assistant (RF-07 · C2, RNF-03 · C2).

5. La persona vuelve antes de 60 s. Esperado: `repetido: true` y la puerta se abre otra vez, sin evento nuevo (R4).

6. Esperado en la web (o en `GET /api/v1/asistencia`) y en el panel «Portería»:
   - la llegada es `tarde`, con sus minutos (R5);
   - el panel muestra asistentes hoy 1 y tarde 1 (RF-06 · C1, RF-07 · C4).

7. En Assist, con el asistente «Portería»:
   - «¿Quién llegó tarde hoy?» responde con la persona y sus minutos (RF-08 · C2);
   - «Abre la puerta» dice que no puede, y la puerta no cambia (RF-08 · C5).
   - Se anota el tiempo de cada respuesta.

8. El otro integrante mira la webcam tres veces en menos de 60 s (si sale `descartado`, que se acerque). Esperado:
   - tres `desconocido`, cada uno con su evento;
   - una notificación de desconocidos en Home Assistant, y la entidad Desconocido detectado encendida 60 s (R6, RF-07 · C3).

9. Registro manual: en Asistencia, registrar a mano la llegada de alguien sin consentimiento (RF-06 · C5). Esperado: el panel se actualiza con el resumen.

10. Anotar el resultado y dejar todo como estaba: el horario «Hito 2» se borra o se le quita a la persona.

### Criterios del hito

- H1 (RF-07 · C1; RF-14 · C4) Las entidades del servidor y de la placa aparecen solas en Home Assistant OS.
- H2 (RF-07 · C2; RNF-03 · C2) Un `permitido` abre la puerta de la placa en menos de 2 s, también en la repetición de R4.
- H3 (R5; RF-06 · C1) La llegada queda `tarde` con sus minutos, y el panel la cuenta.
- H4 (RF-08 · C2 y C5) Assist dice quién llegó tarde con las herramientas de AccesIA y no abre la puerta.
- H5 (R6; RF-07 · C3) Tres desconocidos en 60 s crean una notificación.
- H6 (RF-06 · C5) La llegada manual entra al reporte y al resumen.
- H7 (RNF-01 · C1) Ni el simulador ni el servidor guardaron imágenes: `git status` limpio fuera de `datos/` y el registro del servidor sin imágenes ni base64.
- H8 El resultado queda en la bitácora, con los tiempos medidos.

### Si algo falla

| Síntoma | Dónde mirar |
| --- | --- |
| Home Assistant no ve las entidades | La integración MQTT apunta a `192.168.137.1:1883` con el usuario `homeassistant`; el firewall deja entrar el 1883; el servidor vuelve a publicar el descubrimiento cuando Home Assistant publica `online` en `homeassistant/status` |
| La puerta no se abre | Que la automatización `accesia_abrir_puerta` esté cargada; que el simulador no esté conectado a MQTT con el mismo código que la placa; el tráfico con `mosquitto_sub` (`mqtt.md`, Pruebas) |
| `mqtt` sale `sin_conexion` en salud | `MQTT_URL` del servidor y la clave de `MQTT_SERVIDOR_CLAVE` en `infra/.env` |
| Assist responde sin usar las herramientas | En el agente de Ollama, «Herramientas de IA» marca solo AccesIA; la URL de MCP es la del portátil; el servidor MCP acepta ese encabezado `Host` (B3) |
| Assist tarda más de 15 s | El modelo cargado en memoria; la medición de C2 y D-06 (RNF-03 · C3) |
| La llegada sale `a_tiempo` | La hora del bloque y la tolerancia del horario «Hito 2»; la zona horaria `America/Bogota` en el servidor y en Home Assistant |

## Al terminar

- Una entrada en `docs/bitacora.md`, «Día 3 · Hito 2», con:
  - quién estuvo y qué pasó en cada paso;
  - los tiempos de la puerta y de Assist, y lo que falló.
- Si el hito cambió alguna spec o algún valor de `infra/.env.example`, se actualiza con su versión.
- PR desde `b/hito-2` con la bitácora y esos cambios. Lo que quede pendiente pasa a las tareas del Día 4.
