<!--
Nombre: C2-jhon-home-assistant-y-agente.md
Descripción: Tarea C2 del Día 3 del frente C: Home Assistant OS en la Raspberry Pi 5 con el broker del portátil, automatizaciones, panel Portería y Assist con Ollama y MCP; Ollama, firewall y compose.escenario2.yaml en el portátil; copia de seguridad de Home Assistant OS; primera medición de las 10 preguntas del agente.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Frente C · C2 · Home Assistant y agente

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/home-assistant`
- Depende de:
  - para empezar, la Raspberry Pi 5 con Home Assistant OS, el portátil con Docker Desktop y el hotspot. La primera parte no espera a nadie;
  - B2 del Día 3 en `main`, para las entidades, los eventos, las alertas y el resumen;
  - B3 del Día 3 en `main`, para el servicio `mcp` y la semilla. `compose.escenario2.yaml` lo publica, así que se fusiona después de B3;
  - el PR #11, ya en `main`, da la puerta en el LED de la placa y su temperatura y humedad. Sin la placa, sirve la puerta del simulador (A1).
- Lee primero: `CLAUDE.md`; `tareas/dia-3/00-todos-orden-e-hito-2.md`; `specs/contratos/mqtt.md` completo (Entidades y Automatizaciones); `specs/contratos/mcp-agente.md` (Configuración en Home Assistant, Instrucciones y Evaluación); `specs/requisitos.md` (RF-07, RF-08 y RNF-03 · C2 y C3); `specs/arquitectura.md` (Servicios de Docker Compose y Red y despliegue); `specs/decisiones.md` (D-05, D-06, D-15, D-16, D-19 y D-21); `docs/guia-dia-de-clase.md`; `homeassistant/README.md` e `infra/README.md`.

## Objetivo

Home Assistant OS, en la Pi, ve las entidades de AccesIA por el broker del portátil. Abre la puerta con un acceso permitido, avisa de desconocidos y muestra el panel «Portería». Assist responde con el agente de Ollama y las herramientas MCP de AccesIA.

Queda hecha la primera medición de las 10 preguntas en el portátil (RF-08 · C3), y el portátil ya levanta el escenario 2 de la demo (D-21).

## Antes de empezar

- D-21 adelanta del Día 4 `infra/compose.escenario2.yaml`: es el despliegue de la demo y el Hito 2 lo necesita.
- Lo que se configura en la interfaz de Home Assistant OS no queda en Git: se anota paso a paso en `homeassistant/README.md` y queda en la copia de seguridad (paso 5).
- Propón en el plan:
  - qué archivos de `homeassistant/config/` van al repositorio y cómo se copian a Home Assistant OS (por ejemplo, con el complemento File editor o Samba);
  - cómo se arma el panel «Portería» (en YAML, para que quede en Git);
  - si Ollama corre en Compose (servicio `ollama`) o nativo en Windows, por ejemplo para usar la GPU;
  - cómo se baja el modelo de Ollama la primera vez y dónde queda (en Compose, el volumen `datos-ollama`);
  - si hace falta sumar el servicio `homeassistant` (Home Assistant Container) a `compose.yaml`, para probar en el portátil sin la Pi. Si se suma, `compose.escenario2.yaml` lo quita;
  - si `mcp-agente.md` necesita su versión 1.3 por D-21: las URL de Ollama y del MCP pasan a ser las del portátil (por ejemplo, `http://192.168.137.1:11434` y `http://192.168.137.1:8001/mcp`). Se propone en el PR, como dice `specs/contratos/README.md`.

## Hacer

1. Lo que no espera a nadie:
   - Red: el hotspot de Windows `AccesIA` en 2,4 GHz.
     - El firewall del portátil deja entrar desde `192.168.137.0/24` lo que Home Assistant usa en él: el 1883 (MQTT), el 8001 (MCP) y el 11434 (Ollama). El 8000 se suma cuando la placa envíe recortes (A2).
     - Ollama tiene que escuchar fuera de localhost: en Compose, `compose.escenario2.yaml` publica el 11434; si corre nativo en Windows, con `OLLAMA_HOST=0.0.0.0`.
     - Se documenta en `infra/README.md`, `docs/guia-dia-de-clase.md` y `specs/arquitectura.md` (Red y despliegue), con los comandos de PowerShell.
     - Los cambios del firewall los hace una persona del equipo, no Claude Code.
   - Home Assistant OS en la Pi: zona horaria `America/Bogota` e integración MQTT con `192.168.137.1:1883`, con el usuario `homeassistant` y su clave de `infra/.env`.
   - `homeassistant/config/`:
     - `automatizaciones_accesia.yaml`, con el contenido exacto de `mqtt.md`;
     - las dos líneas de `configuration.yaml` que lo incluyen;
     - el panel «Portería» (RF-07 · C4), con última persona, último resultado, asistentes hoy, llegadas tarde hoy, desconocidos hoy, puerta, cámara en línea y la temperatura y la humedad de la placa.
   - Ollama, como se decida en el plan:
     - en Compose, el servicio `ollama` de `infra/compose.yaml`, con el volumen `datos-ollama` y el modelo de `OLLAMA_MODELO`, sin publicarse en `compose.yaml`;
     - nativo, con `OLLAMA_HOST=0.0.0.0` y el mismo modelo;
     - en los dos casos, el modelo se deja cargado en memoria para evitar la espera del primer mensaje.
   - Las automatizaciones se prueban antes de B2 publicando a mano con `mosquitto_pub` un Evento y una Alerta de `mqtt.md`.
2. Con B3 en `main`:
   - `infra/compose.escenario2.yaml` publica `mcp` (8001) y, si Ollama va en Compose, `ollama` (11434) en la red del portátil (D-16, D-19 y D-21). Quita `homeassistant` si se sumó.
   - Antes de fusionar se revisa con `docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml config`. Después de fusionar, se levanta así en la carpeta principal (acuerdos de `00-todos-orden-e-hito-2.md`):

     ```powershell
     docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml up -d --build
     ```

   - En Home Assistant OS:
     - integración Ollama, con la URL del portátil y el modelo de D-06;
     - integración Model Context Protocol, con la URL del portátil;
     - el agente de Ollama con las instrucciones de `mcp-agente.md`;
     - en «Herramientas de IA» se marca solo AccesIA, y «Control de dispositivos» queda apagado (D-15, RF-08 · C5);
     - el asistente de voz «Portería» en español;
     - en «Exponer», el botón «Abrir puerta» no se expone.
3. Con B2 en `main`:
   - las entidades de `mqtt.md` aparecen solas (RF-07 · C1);
   - un `permitido` abre la puerta de la placa (o del simulador, con A1) y la entidad Puerta cambia en menos de 2 s (RF-07 · C2, RNF-03 · C2);
   - tres desconocidos crean la notificación (RF-07 · C3);
   - el panel muestra todo.
4. Primera medición de las 10 preguntas en el portátil (RF-08 · C3; RNF-03 · C3), con los datos de `semilla agente` y como diga el plan de B3:
   - se anotan en la bitácora el modelo, el equipo, la respuesta y el tiempo de cada pregunta;
   - si no llega a 9 de 10 (la 9 y la 10 son obligatorias), se prueba un modelo más reciente de tamaño parecido y se propone el cambio de D-06 en el PR.
5. Copia de seguridad de Home Assistant OS, pendiente de la lista de infra de D-21:
   - lleva la integración MQTT con el portátil, las de Ollama y MCP, el agente, `automatizaciones_accesia.yaml` y el panel;
   - queda en `kit/`, que Git ignora, y nunca en el repositorio, porque lleva claves;
   - `homeassistant/README.md` dice cómo hacerla y cómo restaurarla.
6. `homeassistant/README.md` (paso a paso en Home Assistant OS), `infra/README.md` (Ollama, firewall y escenario 2), `docs/guia-dia-de-clase.md` y `specs/arquitectura.md` (Red y despliegue).

## No hacer

- No cambies el servidor, el firmware, el simulador ni la ACL de MQTT.
- No le des a Assist control de dispositivos ni expongas la puerta (D-15).
- No subas claves: las de MQTT y del administrador viven en `infra/.env`. Tampoco subas `homeassistant/config/.storage/` ni la base de Home Assistant, que Git ya ignora.
- No publiques `mcp` ni `ollama` en `compose.yaml`: solo `compose.escenario2.yaml` lo hace.
- Las imágenes arm64, el resto del kit y `verificar.sh` son del Día 4.

## Criterios de aceptación

- C1 (RF-07 · C1; RF-14 · C4) Las entidades del servidor y las de ambiente de la placa aparecen solas en Home Assistant OS.
- C2 (RF-07 · C2; RNF-03 · C2) Un acceso permitido, también la repetición de R4, abre la puerta en menos de 2 s, medido.
- C3 (RF-07 · C3 y C4) La alerta de R6 crea una notificación, y el panel «Portería» muestra lo que pide RF-07 · C4.
- C4 (RF-08 · C2 y C5) Assist usa las herramientas de AccesIA con el agente de Ollama y no puede abrir la puerta.
- C5 (RF-08 · C3; RNF-03 · C3) La primera medición de las 10 preguntas queda en la bitácora, con el modelo, el equipo y los tiempos.
- C6 (D-21) `compose.escenario2.yaml` levanta el escenario 2. Home Assistant OS llega a `mcp` y a `ollama` por la red del hotspot, con el firewall abierto solo para `192.168.137.0/24`.
- C7 (RF-11 · C2) La copia de seguridad de Home Assistant OS queda en `kit/`, fuera de Git, y se restaura con los pasos de `homeassistant/README.md`.
- C8 `homeassistant/README.md`, `infra/README.md`, `docs/guia-dia-de-clase.md`, `specs/arquitectura.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué quedó configurado y dónde está anotado;
  - qué pruebas corriste, con su resultado;
  - los tiempos de la puerta y de Assist, y el resultado de las 10 preguntas.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-c`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
