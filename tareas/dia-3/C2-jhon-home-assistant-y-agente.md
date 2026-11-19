<!--
Nombre: C2-jhon-home-assistant-y-agente.md
Descripción: Tarea C2 del Día 3 del frente C, ajustada a D-22: Home Assistant OS en la Raspberry Pi 5 con todo en ella; Mosquitto oficial con la ACL, el complemento de Ollama y su modelo, automatizaciones, panel Portería y Assist con Ollama y el MCP del complemento del servidor (B4 del Día 4); ensayo en el devcontainer; compose.escenario2.yaml como plan B; copia de seguridad de Home Assistant OS; primera medición de las 10 preguntas del agente.
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.2
-->

# Día 3 · Frente C · C2 · Home Assistant y agente

> **Ajustada a D-22 (versión 1.1).** Todo corre en la Pi, como complementos de Home Assistant OS. La base y el servidor (con la web, MQTT y el MCP) son complementos nuestros, que hace la B4 del Día 4. Mosquitto es el complemento oficial, y Ollama el de SirUli. Esta tarea configura Home Assistant OS, Mosquitto y Ollama en la Pi, y conecta Assist con el MCP cuando la B4 esté en `main`. Los archivos de Home Assistant se mantienen: `configuration.yaml`, las automatizaciones y el panel. `compose.escenario2.yaml` queda como plan B. El Hito 2 necesita esta tarea, así que ahora también espera a la B4.

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/home-assistant`
- Depende de:
  - para empezar, la Raspberry Pi 5 con Home Assistant OS e internet para instalar los complementos. Si la Pi solo está disponible en clase, se instala allá con el internet del celular. Sin la Pi, se ensaya en el devcontainer de Home Assistant (ver «Antes de empezar»). La primera parte no espera a nadie;
  - B2 y B3 del Día 3, ya en `main`: las entidades, los eventos, las alertas, el resumen, el servidor MCP y la semilla;
  - la B4 del Día 4 en `main`, con los complementos `accesia_base` y `accesia_servidor`: para las entidades del servidor en la Pi, el MCP, la medición y la copia de seguridad final;
  - el PR #11, ya en `main`, da la puerta en el LED de la placa y su temperatura y humedad. Sin la placa, sirve la puerta del simulador (A1).
- Lee primero: `CLAUDE.md`; `tareas/dia-3/00-todos-orden-e-hito-2.md`; `specs/decisiones.md` (D-05, D-06, D-15, D-16, D-19, D-21 y D-22, con «Cómo se aplica D-22»); `specs/arquitectura.md` («Complementos de Home Assistant OS» y «Red y despliegue»); `specs/contratos/mqtt.md` 1.4 completo (Broker, ACL, Entidades y Automatizaciones); `specs/contratos/mcp-agente.md` 1.4 (Configuración en Home Assistant, Instrucciones y Evaluación); `specs/requisitos.md` (RF-07, RF-08 y RNF-03 · C2 y C3); `docs/guia-dia-de-clase.md`; `homeassistant/README.md` e `infra/README.md`.

## Objetivo

Home Assistant OS, en la Pi, ve las entidades de AccesIA por el Mosquitto oficial de la Pi. Abre la puerta con un acceso permitido, avisa de desconocidos y muestra el panel «Portería». Assist responde con el agente de Ollama, que corre en la Pi, y las herramientas MCP de AccesIA, del complemento del servidor.

Queda hecha la primera medición de las 10 preguntas (RF-08 · C3), con lo que muestre `prompt_eval_count` sobre la caché del prompt, y el plan B (escenario 2) queda listo.

## Antes de empezar

- Lo que se configura en la interfaz de Home Assistant OS no queda en Git: se anota paso a paso en `homeassistant/README.md` y queda en la copia de seguridad (paso 6).
- Sin la Pi, se ensaya con el devcontainer oficial de Home Assistant, que corre Supervisor y Home Assistant en Docker en el portátil (`http://localhost:7123`) y deja instalar complementos locales (`specs/arquitectura.md`, «Cómo se prueban sin la Pi»).
- Propón en el plan:
  - qué archivos de `homeassistant/config/` van al repositorio y cómo se copian a Home Assistant OS (por ejemplo, con el complemento Samba share o File editor);
  - cómo se arma el panel «Portería» (en YAML, para que quede en Git);
  - cómo se copian la ACL a `/share/mosquitto/` y el modelo de Ollama a `/share/ollama`;
  - qué modelos de Ollama se bajan para medir, según la RAM de la Pi (D-22): con 4 GB, `qwen2.5:1.5b`; con 8 GB, `qwen2.5:1.5b` y `qwen2.5:3b`, también en sus variantes Q4_0.

## Hacer

1. Lo que no espera a nadie, en la Pi o en el devcontainer:
   - Red: el hotspot de Windows `AccesIA` en 2,4 GHz, y la IP fija de la Pi en él, desde la configuración de red de Home Assistant OS. Por ejemplo `192.168.137.250`; la que quede se anota en `specs/arquitectura.md` (P-04).
   - Zona horaria `America/Bogota`.
   - El complemento oficial de Mosquitto (`mqtt.md` 1.4):
     - `logins` con `servidor` y `camara`, con las claves de `infra/.env`;
     - `customize` activo con la carpeta `mosquitto`, `/share/mosquitto/acl.conf` con su línea `acl_file` y, en `/share/mosquitto/accesscontrollist`, la ACL de `mqtt.md` 1.4;
     - la integración MQTT de Home Assistant se configura sola, con el usuario `homeassistant`.
   - El complemento de Ollama de SirUli, con el modelo de D-22 en `/share/ollama`, cargado en memoria (`OLLAMA_KEEP_ALIVE=-1`). El complemento publica el 11434 por defecto: en su sección Red se desactiva ese puerto, para que se cumpla D-16. Home Assistant llega a Ollama por la red interna. En sus opciones, `OLLAMA_FLASH_ATTENTION` pasa a 1: con el 0 por defecto y la caché `q8_0`, Ollama 0.40.16 no carga el modelo (`specs/arquitectura.md`, «Complementos de Home Assistant OS»).
   - `homeassistant/config/`, como en la versión 1.0:
     - `automatizaciones_accesia.yaml`, con el contenido exacto de `mqtt.md`;
     - las dos líneas de `configuration.yaml` que lo incluyen;
     - el panel «Portería» (RF-07 · C4), con última persona, último resultado, asistentes hoy, llegadas tarde hoy, desconocidos hoy, puerta, cámara en línea y la temperatura y la humedad de la placa.
   - Las automatizaciones se prueban antes de la B4 publicando a mano con `mosquitto_pub` un Evento y una Alerta de `mqtt.md`, en el Mosquitto de la Pi y con el usuario `servidor`.
   - Con la placa: por su consola serial, `mqtt mqtt://<IP de la Pi>:1883 camara <clave>`. La temperatura y la humedad aparecen solas (RF-14 · C4).
2. Con la B4 en `main`:
   - instalar `accesia_base` y `accesia_servidor` como dice `specs/arquitectura.md` («Complementos de Home Assistant OS»), con las claves y las reglas en sus opciones;
   - en Home Assistant OS:
     - integración Ollama, con la URL del complemento de Ollama y el modelo de D-22;
     - integración Model Context Protocol, con `http://local-accesia-servidor:8001/mcp`. Home Assistant relee las herramientas cada 30 minutos: si se actualizó el servidor MCP, se recarga la integración;
     - el agente de Ollama con las instrucciones de `mcp-agente.md`;
     - en «Herramientas de IA» se marca solo AccesIA, y «Control de dispositivos» queda apagado (D-15, RF-08 · C5);
     - el asistente de voz «Portería» en español;
     - en «Exponer», el botón «Abrir puerta» no se expone.
3. Con la B4 en `main`, se comprueba:
   - las entidades de `mqtt.md` aparecen solas (RF-07 · C1);
   - un `permitido` abre la puerta de la placa (o la del simulador con A1, apuntando al broker de la Pi), y la entidad Puerta cambia en menos de 2 s (RF-07 · C2, RNF-03 · C2);
   - tres desconocidos crean la notificación (RF-07 · C3);
   - el panel muestra todo.
4. Primera medición de las 10 preguntas (RF-08 · C3; RNF-03 · C3), con los datos de `semilla agente` (con `--con-datos-reales` si la base ya tiene datos, y `--borrar` después):
   - en la Pi o, sin ella, en el devcontainer, con el mismo modelo. En el portátil cuenta si responde bien; el tiempo que vale es el de la Pi;
   - se anotan en la bitácora el modelo, el equipo, la respuesta y el tiempo de cada pregunta;
   - la caché del prompt: con `mcp-agente.md` 1.5, Home Assistant no agrega su línea de fecha y hora, y la segunda pregunta solo procesa la pregunta. Ya se midió en el portátil con `servidor/scripts/cache_del_prompt.py` (`specs/arquitectura.md`, «Velocidad del agente en la Pi»). En el devcontainer se repite con el mismo script, apuntando al Ollama del complemento; en la Pi se anota el tiempo de la segunda pregunta;
   - si no llega a 9 de 10 (la 9 y la 10 son obligatorias), se prueba un modelo más reciente de tamaño parecido y se propone el cambio de D-06 en el PR;
   - si una respuesta pasa de 15 s en la Pi, se sigue RNF-03 · C3: primero se prueba en la Pi, y Ollama solo pasa al portátil con el visto bueno del profesor.
5. Plan B, `infra/compose.escenario2.yaml` (el escenario 2 de D-21, para cuando la Pi no alcance para la base y el servidor):
   - quita `homeassistant`, si se sumó a `compose.yaml`, y publica `mcp` (8001) en la red del portátil. Ollama sigue en la Pi;
   - se revisa con `docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml config`;
   - el firewall del portátil deja entrar desde `192.168.137.0/24` el 1883 y el 8001, y el 8000 cuando la placa envíe recortes. Los cambios del firewall los hace una persona del equipo, no Claude Code;
   - se prueba una vez con la Pi: Home Assistant OS llega al broker y a `mcp` del portátil;
   - se anota en `infra/README.md` y en `docs/guia-dia-de-clase.md`, con los comandos de PowerShell.
6. Copia de seguridad de Home Assistant OS:
   - lleva Mosquitto con sus `logins` y la ACL, los complementos, las integraciones de Ollama y MCP, el agente, `automatizaciones_accesia.yaml` y el panel. El modelo de Ollama va aparte en el kit;
   - se toma cifrada y sin inscripciones, porque incluye la base, es decir, las huellas (D-22);
   - queda en `kit/`, que Git ignora, y nunca en el repositorio, porque lleva claves;
   - `homeassistant/README.md` dice cómo hacerla y cómo restaurarla.
7. `homeassistant/README.md` (paso a paso en Home Assistant OS), `infra/README.md` (plan B), `docs/guia-dia-de-clase.md` y `specs/arquitectura.md` (la IP de la Pi en «Red y despliegue»).

## No hacer

- No cambies el servidor, el firmware, el simulador, los complementos de AccesIA (son de la B4) ni `infra/mosquitto/acl`, que la B4 pone al día con `mqtt.md` 1.4.
- No le des a Assist control de dispositivos ni expongas la puerta (D-15).
- No subas claves: las de MQTT y del administrador viven en `infra/.env` y en las opciones de los complementos. Tampoco subas `homeassistant/config/.storage/` ni la base de Home Assistant, que Git ya ignora.
- No publiques el MCP ni Ollama fuera de la Pi (D-16). En el portátil, solo `compose.escenario2.yaml` publica `mcp`, y solo para el plan B.
- El resto del kit y `verificar` son del Día 4.

## Criterios de aceptación

- C1 (RF-07 · C1; RF-14 · C4) Las entidades del servidor y las de ambiente de la placa aparecen solas en Home Assistant OS, por el Mosquitto de la Pi.
- C2 (RF-07 · C2; RNF-03 · C2) Un acceso permitido, también la repetición de R4, abre la puerta en menos de 2 s, medido.
- C3 (RF-07 · C3 y C4) La alerta de R6 crea una notificación, y el panel «Portería» muestra lo que pide RF-07 · C4.
- C4 (RF-08 · C2 y C5) Assist usa las herramientas de AccesIA con el agente de Ollama de la Pi y no puede abrir la puerta.
- C5 (RF-08 · C3; RNF-03 · C3) La primera medición de las 10 preguntas queda en la bitácora, con el modelo, el equipo, los tiempos y lo que mostró `prompt_eval_count`.
- C6 (D-22) El MCP y Ollama no se publican fuera de la Pi: el 11434 del complemento de Ollama queda desactivado en su sección Red, y Home Assistant los alcanza por la red interna. Mosquitto usa la ACL de `mqtt.md` 1.4.
- C7 (D-22, plan B) `compose.escenario2.yaml` pasa `docker compose … config` y se probó una vez con la Pi, con el firewall abierto solo para `192.168.137.0/24`.
- C8 (RF-11 · C2) La copia de seguridad de Home Assistant OS, cifrada y sin inscripciones, queda en `kit/`, fuera de Git, y se restaura con los pasos de `homeassistant/README.md`.
- C9 `homeassistant/README.md`, `infra/README.md`, `docs/guia-dia-de-clase.md`, `specs/arquitectura.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué quedó configurado y dónde está anotado;
  - qué pruebas corriste, con su resultado;
  - los tiempos de la puerta y de Assist, el resultado de las 10 preguntas y lo que mostró `prompt_eval_count`.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-c`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
