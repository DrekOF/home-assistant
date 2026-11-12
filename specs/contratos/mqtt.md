<!--
Nombre: mqtt.md
Descripción: Contrato MQTT de AccesIA: temas, mensajes, descubrimiento de Home Assistant y automatizaciones.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Contrato MQTT · versión 1.2

Lo cumplen el servidor (frente B), la placa y el simulador (frente A) y Home Assistant (frente C). En este contrato, «cámara» es el dispositivo de un punto de acceso, con su `{codigo}`: la placa (una XIAO ESP32-C6 en la demo, D-21) o el simulador.

## Broker

- Mosquitto 2 en el puerto 1883, sin acceso anónimo.
- En la demo (D-21) es el Mosquitto del compose del portátil, en la IP fija del hotspot de Windows (suele ser `192.168.137.1`). Home Assistant OS, en la Pi, se conecta a él con el usuario `homeassistant`.
- Tres usuarios, con claves en `infra/.env`: `servidor`, `homeassistant` y `camara` (la usan las cámaras y el simulador).
- `{codigo}` es el código de la cámara, por ejemplo `entrada`. En los `entity_id` de Home Assistant los guiones del código pasan a guion bajo.
- `servidor` está reservado: es el `{codigo}` de los temas del servidor y ninguna cámara puede usarlo (el SQL y la API lo rechazan).
- Cada cámara, y el simulador, se conecta con su código como client id: la ACL usa `%c` para dejarla solo en sus temas. Dos clientes con el mismo client id se desconectan entre sí, así que una cámara y el simulador no pueden usar el mismo código a la vez.

ACL de Mosquitto (`infra/mosquitto/acl`):

```text
user servidor
topic readwrite accesia/#
topic readwrite homeassistant/#

user homeassistant
topic readwrite homeassistant/#
topic read accesia/#
topic write accesia/+/puerta/set

user camara
topic deny accesia/servidor/#

# %c es el client id. Mosquitto aplica las líneas pattern a todos los usuarios;
# al usuario camara solo le dan acceso estas.
pattern read accesia/%c/puerta/set
pattern write accesia/%c/puerta/estado
pattern write accesia/%c/estado
pattern write accesia/%c/disponible

# La placa publica sus lecturas de ambiente y el descubrimiento de sus dos sensores (D-21).
# %c tiene que ocupar un nivel entero del tema: por eso el nodo del descubrimiento es el código.
pattern write accesia/%c/ambiente
pattern write homeassistant/sensor/%c/temperatura/config
pattern write homeassistant/sensor/%c/humedad/config
```

La línea `deny` impide que un cliente con el usuario `camara` y el client id `servidor` publique en nombre del servidor. Como el código no lleva guion bajo, el nodo de la placa (por ejemplo, `entrada`) nunca coincide con uno del servidor (`accesia_entrada`, `accesia_servidor`).

## Temas

| Tema | Publica | Escucha | Mensaje | QoS | Retenido |
| --- | --- | --- | --- | --- | --- |
| `accesia/servidor/disponible` | servidor (último deseo) | Home Assistant | `online` / `offline` | 1 | Sí |
| `accesia/{codigo}/evento` | servidor | Home Assistant | JSON Evento | 1 | No |
| `accesia/{codigo}/alerta` | servidor | Home Assistant | JSON Alerta (R6) | 1 | No |
| `accesia/resumen` | servidor | Home Assistant | JSON Resumen | 1 | Sí |
| `accesia/{codigo}/disponible` | cámara (último deseo) | Home Assistant, servidor | `online` / `offline` | 1 | Sí |
| `accesia/{codigo}/estado` | cámara | Home Assistant, servidor | JSON EstadoCamara, cada 60 s | 0 | Sí |
| `accesia/{codigo}/ambiente` | placa | Home Assistant | JSON Ambiente, cada 30 s | 0 | Sí |
| `accesia/{codigo}/puerta/set` | Home Assistant | cámara | `ABRIR` o `CERRAR` | 1 | No |
| `accesia/{codigo}/puerta/estado` | cámara | Home Assistant | `abierta` / `cerrada` | 1 | Sí |
| `homeassistant/status` | Home Assistant | servidor | `online` / `offline` | — | — |
| `homeassistant/{componente}/{nodo}/{objeto}/config` | servidor; la placa, solo el de sus dos sensores de ambiente | Home Assistant | JSON de descubrimiento | 1 | Sí |

- Los eventos no son retenidos para que una automatización no se repita cuando Home Assistant se reinicia.
- Una repetición de R4 de un `permitido` se publica en `accesia/{codigo}/evento` con `repetido: true`, para que la automatización abra la puerta otra vez. Una repetición de un `denegado` no se publica.
- Al recibir `ABRIR`, la cámara mantiene la puerta abierta los segundos configurados (3 por defecto), publica `abierta` y luego `cerrada`. `CERRAR` la cierra antes.
- Cada 30 s la placa lee su sensor y publica `ambiente`. Si una lectura falla, no publica; a la tercera falla seguida publica `null` en los dos campos, y Home Assistant los muestra como desconocidos. Con la primera lectura buena vuelve a publicar los valores.
- El servidor publica el descubrimiento al arrancar, cuando Home Assistant publica `online` en `homeassistant/status` y cuando se crea o cambia una cámara. La placa publica el de sus dos sensores de ambiente cada vez que se conecta al broker (ver «Entidades que publica la placa»).
- El servidor publica el resumen al arrancar, después de cada evento guardado, después de cada llegada registrada a mano (RF-06 · C5) y cada 5 minutos (así cambia de día a medianoche).

## Mensajes

Evento (`asistencia` solo viene cuando este evento creó la llegada del día; si no, es `null`):

```json
{
  "evento_id": "01a1e6d0-1c2b-7e3f-8a9b-0c1d2e3f4a5b",
  "dispositivo": "entrada",
  "resultado": "permitido",
  "motivo": null,
  "persona": { "id": "01a1e5c2-7f3a-7b2c-9d4e-5f6a7b8c9d0e", "nombre": "Ana Gómez" },
  "similitud": 0.71,
  "repetido": false,
  "asistencia": { "estado": "a_tiempo", "minutos_tarde": null },
  "hora": "2026-11-20T06:58:12-05:00"
}
```

`repetido` es `true` solo en la repetición de un `permitido` (R4). Entonces `evento_id` es el del evento original; `persona`, `similitud` y `hora` son los de este recorte, y `asistencia` es `null`.

Con `desconocido`, `persona` es `null`: nunca se publica a quién se parece.

Alerta:

```json
{ "dispositivo": "entrada", "desconocidos": 3, "ventana_s": 60, "hora": "2026-11-20T08:15:41-05:00" }
```

Resumen:

```json
{
  "fecha": "2026-11-20",
  "asistentes": 4,
  "a_tiempo": 2,
  "tarde": 1,
  "sin_horario": 1,
  "desconocidos_hoy": 3,
  "ultima_llegada": { "nombre": "David Peña", "hora": "2026-11-20T07:40:05-05:00" },
  "hora": "2026-11-20T08:20:00-05:00"
}
```

Ambiente (D-21): la temperatura en °C y la humedad relativa en %, con un decimal. La placa no tiene hora, por eso no la envía.

```json
{ "temperatura": 24.6, "humedad": 58.0 }
```

Tras 3 lecturas fallidas seguidas:

```json
{ "temperatura": null, "humedad": null }
```

EstadoCamara (la cámara puede no tener hora, por eso no la envía). `firmware` es el mismo texto de la cabecera `X-AccesIA-Firmware` de `api-dispositivo.md`. El simulador no envía `perfil`, `rssi`, `psram_kb` ni `libre_kb`. La XIAO ESP32-C6 no envía `psram_kb`, porque no tiene PSRAM, y suma dos campos opcionales: `sensor` (`dht22` o `dht11`) y `antena` (`interna` o `externa`).

De la XIAO ESP32-C6:

```json
{ "perfil": "xiao_esp32c6", "firmware": "tinyml-xiao_esp32c6-1.0.0", "ip": "192.168.137.23", "rssi": -52, "libre_kb": 210, "sensor": "dht22", "antena": "interna", "segundos_encendida": 5321 }
```

Del ESP32-S3 de referencia (PR #7):

```json
{ "perfil": "esp32s3_eye", "firmware": "tinyml-esp32s3_eye-1.0.0", "ip": "10.42.0.23", "rssi": -58, "psram_kb": 8192, "libre_kb": 3120, "segundos_encendida": 5321 }
```

## Entidades de Home Assistant (descubrimiento)

Por cada cámara, en el dispositivo «AccesIA {nombre}» (identificador `accesia_{codigo}`):

| Entidad | Componente | `default_entity_id` | Estado desde | Disponibilidad |
| --- | --- | --- | --- | --- |
| Última persona | `sensor` | `sensor.accesia_{codigo}_ultima_persona` | `accesia/{codigo}/evento` | servidor |
| Último resultado | `sensor` | `sensor.accesia_{codigo}_ultimo_resultado` | `accesia/{codigo}/evento` | servidor |
| Desconocido detectado | `binary_sensor` (`problem`) | `binary_sensor.accesia_{codigo}_desconocido` | `accesia/{codigo}/alerta`; se apaga solo a los 60 s | servidor |
| Puerta | `binary_sensor` (`door`) | `binary_sensor.accesia_{codigo}_puerta` | `accesia/{codigo}/puerta/estado` | cámara |
| Abrir puerta | `button` | `button.accesia_{codigo}_abrir_puerta` | Publica `ABRIR` en `accesia/{codigo}/puerta/set` | cámara |
| Cámara en línea | `binary_sensor` (`connectivity`) | `binary_sensor.accesia_{codigo}_en_linea` | `accesia/{codigo}/disponible` | — |

En el dispositivo «AccesIA Servidor» (identificador `accesia_servidor`):

| Entidad | Componente | `default_entity_id` | Estado desde |
| --- | --- | --- | --- |
| Asistentes hoy | `sensor` | `sensor.accesia_asistentes_hoy` | `accesia/resumen` → `asistentes` |
| Llegadas tarde hoy | `sensor` | `sensor.accesia_tarde_hoy` | `accesia/resumen` → `tarde` |
| Desconocidos hoy | `sensor` | `sensor.accesia_desconocidos_hoy` | `accesia/resumen` → `desconocidos_hoy` |
| Servidor en línea | `binary_sensor` (`connectivity`) | `binary_sensor.accesia_servidor_en_linea` | `accesia/servidor/disponible` |

«Disponibilidad servidor» es `availability_topic: accesia/servidor/disponible`; «cámara» es `accesia/{codigo}/disponible`. Se usa `default_entity_id` porque `object_id` ya no lo acepta Home Assistant.

Ejemplo completo, «Última persona» de la cámara `entrada`, en `homeassistant/sensor/accesia_entrada/ultima_persona/config`:

```json
{
  "name": "Última persona",
  "unique_id": "accesia_entrada_ultima_persona",
  "default_entity_id": "sensor.accesia_entrada_ultima_persona",
  "state_topic": "accesia/entrada/evento",
  "value_template": "{{ value_json.persona.nombre if value_json.persona else 'Desconocido' }}",
  "json_attributes_topic": "accesia/entrada/evento",
  "icon": "mdi:account-badge",
  "availability_topic": "accesia/servidor/disponible",
  "device": {
    "identifiers": ["accesia_entrada"],
    "name": "AccesIA Entrada",
    "manufacturer": "Equipo AccesIA",
    "model": "XIAO ESP32-C6",
    "sw_version": "1.0.0"
  },
  "origin": { "name": "AccesIA servidor", "sw_version": "1.0.0" }
}
```

Otros campos que cambian por entidad:

- Último resultado: `"value_template": "{{ value_json.resultado }}"`.
- Desconocido detectado: `"value_template": "{{ 'ON' }}"`, `"off_delay": 60`, `"device_class": "problem"`.
- Puerta: `"payload_on": "abierta"`, `"payload_off": "cerrada"`, `"device_class": "door"`.
- Abrir puerta: `"command_topic": "accesia/{codigo}/puerta/set"`, `"payload_press": "ABRIR"`.
- Cámara en línea y Servidor en línea: `"payload_on": "online"`, `"payload_off": "offline"`, `"device_class": "connectivity"`.
- Sensores del resumen: `"value_template": "{{ value_json.asistentes }}"` (o `tarde`, `desconocidos_hoy`), `"unit_of_measurement": "personas"`, `"state_class": "measurement"`.

### Entidades que publica la placa (D-21)

La placa publica el descubrimiento de sus dos sensores de ambiente, para que se vean en Home Assistant aunque el servidor esté apagado. Quedan en el mismo dispositivo de la cámara, porque Home Assistant agrupa por `device.identifiers`.

| Entidad | Componente | `default_entity_id` | Estado desde | Disponibilidad |
| --- | --- | --- | --- | --- |
| Temperatura | `sensor` (`temperature`, °C) | `sensor.accesia_{codigo}_temperatura` | `accesia/{codigo}/ambiente` → `temperatura` | cámara |
| Humedad | `sensor` (`humidity`, %) | `sensor.accesia_{codigo}_humedad` | `accesia/{codigo}/ambiente` → `humedad` | cámara |

- Temas: `homeassistant/sensor/{codigo}/temperatura/config` y `homeassistant/sensor/{codigo}/humedad/config`. El nodo es el código tal cual, y no `accesia_{codigo}` como en los temas del servidor, porque la ACL usa `%c` y Mosquitto exige que ocupe un nivel entero del tema.
- `device` lleva solo `identifiers` (`accesia_{codigo}`). El nombre, el fabricante y el modelo del dispositivo los pone el servidor, y la placa no los pisa.
- `unique_id` y `default_entity_id` llevan el código con los guiones pasados a guion bajo, como las demás entidades.
- La placa publica los dos config, retenidos, cada vez que se conecta al broker. Antes de cambiar de código (comando `codigo`), borra los suyos con un mensaje vacío retenido, porque con el código nuevo la ACL ya no la deja. La API no borra cámaras: si una placa se retira, sus dos config se borran a mano, como se muestra en «Pruebas».

Ejemplo completo, «Temperatura» de la cámara `entrada`, en `homeassistant/sensor/entrada/temperatura/config`:

```json
{
  "name": "Temperatura",
  "unique_id": "accesia_entrada_temperatura",
  "default_entity_id": "sensor.accesia_entrada_temperatura",
  "state_topic": "accesia/entrada/ambiente",
  "value_template": "{{ value_json.temperatura }}",
  "device_class": "temperature",
  "unit_of_measurement": "°C",
  "state_class": "measurement",
  "suggested_display_precision": 1,
  "availability_topic": "accesia/entrada/disponible",
  "device": { "identifiers": ["accesia_entrada"] },
  "origin": { "name": "AccesIA firmware", "sw_version": "1.0.0" }
}
```

Humedad cambia en `"value_template": "{{ value_json.humedad }}"`, `"device_class": "humidity"` y `"unit_of_measurement": "%"`. Con `null` en el mensaje, la plantilla da `None` y Home Assistant muestra el sensor como desconocido.

## Automatizaciones de Home Assistant

La regla del servidor ya decidió el acceso (D-03); Home Assistant solo abre la puerta y avisa. Van en un archivo propio, `homeassistant/config/automatizaciones_accesia.yaml`, que `configuration.yaml` incluye aparte del archivo que usa la interfaz:

```yaml
automation ui: !include automations.yaml
automation accesia: !include automatizaciones_accesia.yaml
```

Home Assistant no deja editar desde la interfaz las automatizaciones de ese archivo, así que nunca lo reescribe ni le borra el encabezado o los comentarios. Contenido de `automatizaciones_accesia.yaml`:

```yaml
- id: accesia_abrir_puerta
  alias: "AccesIA · Abrir la puerta con acceso permitido"
  mode: queued
  triggers:
    - trigger: mqtt
      topic: "accesia/+/evento"
  conditions:
    - condition: template
      value_template: "{{ trigger.payload_json.resultado == 'permitido' }}"
  actions:
    - action: mqtt.publish
      data:
        topic: "accesia/{{ trigger.payload_json.dispositivo }}/puerta/set"
        payload: "ABRIR"
        qos: 1

- id: accesia_avisar_desconocidos
  alias: "AccesIA · Avisar desconocidos"
  mode: single
  triggers:
    - trigger: mqtt
      topic: "accesia/+/alerta"
  actions:
    - action: persistent_notification.create
      data:
        title: "Desconocidos en {{ trigger.payload_json.dispositivo }}"
        message: >-
          {{ trigger.payload_json.desconocidos }} caras desconocidas en
          {{ trigger.payload_json.ventana_s }} s, a las
          {{ as_timestamp(trigger.payload_json.hora) | timestamp_custom('%H:%M') }}.
    # Con la app de Home Assistant en un celular se agrega: action: notify.mobile_app_<nombre>
```

## Pruebas

- El servidor prueba que publica cada mensaje con su tema, QoS y retención (marca `contrato MQTT · <tema>`), y que un `permitido` repetido se publica con `repetido: true` y un `denegado` repetido no (`contrato MQTT · repetido`).
- El firmware prueba, sin placa, que arma el mensaje Ambiente y los dos config de su descubrimiento como en este contrato (marcas `contrato MQTT · ambiente` y `contrato MQTT · descubrimiento de la placa`).
- La prueba `contrato MQTT · acl` del servidor comprueba que la placa puede publicar en sus tres temas nuevos y no en los de otro código.
- Para mirar el tráfico:

```powershell
docker compose -f infra/compose.yaml exec mosquitto mosquitto_sub -u servidor -P "<clave>" -t "accesia/#" -v
```

- Para borrar a mano el config retenido de una placa que se retiró (aquí, `entrada`; lo mismo con `humedad`):

```powershell
docker compose -f infra/compose.yaml exec mosquitto mosquitto_pub -u servidor -P "<clave>" -r -n -t "homeassistant/sensor/entrada/temperatura/config"
```
