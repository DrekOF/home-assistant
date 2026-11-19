<!--
Nombre: README.md
Descripción: Home Assistant OS de AccesIA en la Raspberry Pi 5 (D-22): qué archivos van al repositorio, cómo se copian a la Pi y cómo se configuran Mosquitto y Ollama (frente C).
Fecha de creación: 2026-11-11
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 2.1
-->

# Home Assistant · frente C

En la demo, Home Assistant OS corre en la Raspberry Pi 5, y lo demás va como complementos (D-22). Lo que se configura en la interfaz no queda en Git: queda anotado aquí y en la copia de seguridad. El orden del día de clase, con lo que se debe ver en cada paso, está en `docs/guia-dia-de-clase.md`.

## Qué hay en esta carpeta

| Archivo | Qué es | Dónde va en la Pi |
| --- | --- | --- |
| `config/configuration.yaml` | El de fábrica, con las automatizaciones de AccesIA aparte y el panel «Portería» | `/config/configuration.yaml` |
| `config/automatizaciones_accesia.yaml` | Abrir la puerta y avisar desconocidos: el contenido exacto de `contratos/mqtt.md` | `/config/` |
| `config/porteria.yaml` | El panel «Portería» (RF-07 · C4) | `/config/` |
| `mosquitto/acl.conf` | La línea que le dice al complemento de Mosquitto dónde está la ACL | `/share/mosquitto/` |
| `pruebas/evento-permitido.json` y `pruebas/alerta.json` | El Evento y la Alerta de ejemplo de `contratos/mqtt.md` | No van: los usa el script de abajo |
| `scripts/probar-automatizaciones.ps1` | Prueba las dos automatizaciones sin el servidor | No va: se corre en el portátil |

- Las entidades llegan solas por MQTT, con descubrimiento: no se escriben a mano.
- `.storage/` y la base de Home Assistant no van al repositorio, y Git ya las ignora: ahí quedan las integraciones y sus claves.
- Las claves salen de `infra/.env` y van en las opciones de cada complemento, nunca en el repositorio.

## Copiar los archivos a la Pi

Con el complemento Samba share (guía, paso 4), desde el Explorador de Windows:

1. En `\\192.168.137.250\config\`, copia `automatizaciones_accesia.yaml` y `porteria.yaml`.
2. `configuration.yaml`:
   - si sigue como vino de fábrica, reemplázalo por el del repositorio;
   - si no, cambia la línea `automation: !include automations.yaml` por las dos de `contratos/mqtt.md` y agrega al final el bloque `lovelace:` del archivo del repositorio.
3. La zona horaria (`America/Bogota`) y el idioma se ponen en la interfaz, en Configuración → Sistema → General. Así quedan editables.
4. En Home Assistant, Herramientas para desarrolladores → YAML → «Comprobar configuración». Si sale bien, «Reiniciar».

Qué se ve:

- En Configuración → Automatizaciones y escenas aparecen «AccesIA · Abrir la puerta con acceso permitido» y «AccesIA · Avisar desconocidos». No se pueden editar, porque vienen de YAML.
- En la barra lateral aparece «Portería». Sus tarjetas quedan «No disponible» hasta que la placa y el servidor publiquen sus entidades.

## Mosquitto (complemento oficial)

1. Por Samba, en `\\192.168.137.250\share\mosquitto\` (si la carpeta no existe, se crea), copia dos archivos:
   - `acl.conf`, de `homeassistant/mosquitto/acl.conf`;
   - `accesscontrollist`, sin extensión.
     - Es una copia de `infra/mosquitto/acl`, la ACL de `contratos/mqtt.md`, que la B4 puso al día.
     - Va con fin de línea LF, que VS Code muestra abajo a la derecha: con CRLF, Mosquitto no reconoce los temas.
2. Configuración → Complementos → Tienda de complementos → «Mosquitto broker» → Instalar.
3. En su pestaña Configuración, ⋮ → «Editar en YAML»:

   ```yaml
   logins:
     - username: servidor
       password: "<MQTT_SERVIDOR_CLAVE de infra/.env>"
     - username: camara
       password: "<MQTT_CAMARA_CLAVE de infra/.env>"
   require_certificate: false
   certfile: fullchain.pem
   keyfile: privkey.pem
   customize:
     active: true
     folder: mosquitto
   ```

   `homeassistant` y `addons` no van en `logins`: los registra Home Assistant OS (`contratos/mqtt.md`, Broker).
4. Inicia el complemento, con «Iniciar al arrancar» y «Watchdog» activos.
5. Llega la notificación de que se descubrió el Mosquitto broker: Configurar → Enviar. La integración MQTT queda con el usuario `homeassistant`.

Qué se ve:

- El registro del complemento no muestra errores.
- La integración MQTT aparece en Dispositivos y servicios.
- El script de abajo recibe el ABRIR, lo que confirma que la clave de `servidor` y la ACL funcionan.

## Ollama (complemento de SirUli)

1. Por Samba, copia las carpetas `kit\ollama\blobs` y `kit\ollama\manifests` del portátil a `\\192.168.137.250\share\ollama\`.
   - Quedan en `/share/ollama/blobs` y `/share/ollama/manifests`, donde el complemento busca los modelos (`OLLAMA_MODELS: /share/ollama`).
   - Son 2,8 GB: `qwen2.5:1.5b` (986 MB) y `qwen2.5:3b` (1,9 GB).
   - Ver «El kit de Ollama» más abajo.
2. Tienda de complementos → ⋮ → Repositorios → `https://github.com/SirUli/homeassistant-ollama-addon` → Agregar. Después instala «Ollama», versión 0.40.16.
3. En su Configuración:
   - **`OLLAMA_FLASH_ATTENTION`:** `1`. Con el 0 de fábrica y la caché `q8_0`, Ollama 0.40.16 no carga el modelo («quantized V cache requires flash_attn to be enabled»; `specs/arquitectura.md`).
   - **Lo demás, como viene:** `OLLAMA_MODELS: /share/ollama`, `OLLAMA_KEEP_ALIVE: -1` (el modelo queda en memoria), `OLLAMA_KV_CACHE_TYPE: q8_0`, `OLLAMA_NUM_PARALLEL: 1` y `OLLAMA_MAX_LOADED_MODELS: 1`.
   - **Red:** borra el puerto 11434 y guarda. Así no se publica en la red del hotspot (D-16), y Home Assistant llega por la red interna.
4. Inicia el complemento. En su pestaña Información aparece su nombre en la red interna, `<hash>-ollama`.

Qué se ve:

- El registro dice que Ollama escucha en el 11434, con la versión 0.40.16.
- Al agregar la integración Ollama con `http://<hash>-ollama:11434` (guía, paso 9), la lista de modelos trae `qwen2.5:1.5b` y `qwen2.5:3b` sin bajar nada.
- Si Supervisor reinicia el complemento una y otra vez después de borrar el puerto, apaga su Watchdog y anótalo.

### El kit de Ollama

- `kit/ollama/` está en la carpeta principal del repositorio, y Git lo ignora.
- Tiene la estructura de `OLLAMA_MODELS`, que es `blobs/` más `manifests/registry.ollama.ai/library/qwen2.5/{1.5b,3b}`. No lleva la llave de identidad de Ollama, que el complemento guarda en su `/data`.
- Ollama 0.40 suma otras dos carpetas: `metadata/`, una caché que arma solo al cargar cada modelo, y `manifests-v2/`, que está vacía. Da lo mismo copiarlas o no: sin ellas, el complemento las vuelve a crear.
- Se armó el 2026-11-18:
  - el 1.5b se copió del volumen `ollama-cache`;
  - el 3b se bajó con `ollama pull` en un contenedor `ollama/ollama:0.40.16` con `OLLAMA_MODELS` apuntando al kit.
- Prueba: con esa imagen, las opciones de arriba y el kit montado, los dos modelos cargan con flash attention y caché `q8_0`, y responden.
- Las variantes Q4_0 que menciona D-22 no están en el kit: se bajan en la Pi con internet, si hacen falta.

## Probar las automatizaciones sin el servidor

Se hace antes de la B4, con el usuario `servidor` y el broker de la Pi, desde la raíz del repositorio en el portátil y con Docker Desktop abierto:

```powershell
.\homeassistant\scripts\probar-automatizaciones.ps1
```

- **El Evento:** el script publica el Evento `permitido` y espera el ABRIR de Home Assistant. Con la placa conectada, el LED se enciende 3 s (RF-07 · C2).
- **La Alerta:** el script la publica, y en la campana aparece «Desconocidos en entrada» con «3 caras desconocidas en 60 s, a las 08:15» (RF-07 · C3). Si dice otra hora, la zona horaria de Home Assistant no es `America/Bogota`.
- **Después:** los mensajes son los ejemplos del contrato, así que «Última persona» queda en «Ana Gómez» hasta el siguiente acceso real.
- **Plan B:** con la D-23, el broker sigue siendo el de la Pi, así que se corre igual. `-Broker 192.168.137.1` es solo para cuando el broker vuelve al portátil, y `-Broker <IP>`, si la Pi quedó en otra IP.

Probado el 2026-11-18:

- contra el broker del portátil, con un contenedor que respondía como Home Assistant: publica, recibe el ABRIR y no deja la clave en la sesión;
- con el broker inalcanzable: en menos de un minuto dice qué revisar, sin colgarse.

Contra Home Assistant de verdad se prueba en clase.

## Con los complementos de la B4

Pendiente para la clase: lo pide la C2 del Día 3 (paso 2), y se hace con `accesia_base` y `accesia_servidor` ya instalados en la Pi (`complementos/README.md`; guía, paso 7).

- **Integración Ollama:** con `http://<hash>-ollama:11434` y el modelo según la RAM (D-22).
- **Integración Model Context Protocol:** con `http://local-accesia-servidor:8001/mcp`; en el plan B, `http://192.168.137.1:8001/mcp`. Si el servidor MCP cambia, se recarga la integración.
- **El agente de Ollama:** con las instrucciones de `contratos/mcp-agente.md`. En «Herramientas de IA» se marca solo AccesIA, y «Control de dispositivos» queda apagado (D-15).
- **El asistente de voz «Portería»:** en español.
- **«Exponer»:** el botón «Abrir puerta» no se expone.

## Copia de seguridad

Pendiente, para cuando los complementos estén en la Pi (C2, paso 6). Lleva Mosquitto con sus `logins` y la ACL, los complementos, las integraciones, el agente, las automatizaciones y el panel. El modelo de Ollama no entra, porque el complemento lo excluye (`backup_exclude`).

Se toma cifrada y sin inscripciones, porque incluye la base con las huellas. Queda en `kit/` y nunca en el repositorio.

## Lo que no se hace

- Assist no tiene control de dispositivos, y la puerta no se expone (D-15).
- Ni el MCP ni Ollama se publican fuera de la Pi (D-16).
- `infra/mosquitto/acl` es del frente B, y la B4 lo puso al día; aquí solo se dice cómo se copia al complemento.
