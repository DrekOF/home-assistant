<!--
Nombre: guia-dia-de-clase.md
Descripción: Guía para montar AccesIA el día de la clase, en orden y con lo que se debe ver en cada paso: hotspot, la Pi con Home Assistant OS, Mosquitto, la placa, los archivos de Home Assistant, los complementos o el plan B, la cámara y Ollama (D-21 y D-22).
Fecha de creación: 2026-11-11
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 2.0
-->

# Guía del día de clase

Meta: pasar de las cajas cerradas a la primera persona reconocida en menos de 45 minutos, sin depender del internet de la universidad.

El hardware ya se conoce (D-21): una Seeed Studio XIAO ESP32-C6 y una Raspberry Pi 5 con Home Assistant OS. En la demo todo corre en la Pi, como complementos de Home Assistant OS, en el hotspot de Windows del portátil (D-22). El escenario 2, con la base y el servidor en el portátil, queda como plan B.

- **Las claves:** salen de `infra/.env` del portátil y no se escriben en el repositorio ni en esta guía.
- **«Se ve»:** cada paso termina con lo que se debe ver. Si no se ve, no se sigue: se arregla primero.
- **Los detalles de Home Assistant:** cada complemento y cada archivo están en `homeassistant/README.md`.

## Antes de salir

- [ ] El repositorio en `main`, con `infra/.env` y las claves de MQTT del Día 1.
- [ ] `kit\ollama\` en la carpeta principal: 2,8 GB, con `qwen2.5:1.5b` y `qwen2.5:3b`, para `/share/ollama` sin internet (`homeassistant/README.md`, «El kit de Ollama»).
- [ ] El binario del C6, del kit de la sesión 1 (hoy está en `firmware\build-c6`), con ESP-IDF 5.4.4 o esptool.
- [ ] Docker Desktop con las imágenes del plan B ya construidas (`docker compose -f infra/compose.yaml up -d --build` una vez) y `eclipse-mosquitto:2`, que usa el script de prueba.
- [ ] Si la B4 está en `main`, `kit\complementos\`, que arma su script.
- [ ] El celular con datos: el portátil necesita una conexión para encender el hotspot, y los complementos, internet para instalarse.
- [ ] El cable USB-C de datos, el módulo DHT y sus cables.

## 1. Hotspot y firewall (portátil)

1. En Windows 11: Configuración → Red e Internet → Zona con cobertura inalámbrica móvil → Propiedades → Editar:
   - nombre `AccesIA`;
   - la contraseña del equipo, de 8 a 63 caracteres;
   - banda de red de 2,4 GHz, porque el C6 no usa 5 GHz.
2. Enciende la zona. Windows solo la enciende si el portátil tiene una conexión que compartir: la del salón o la del celular.
3. Revisa la IP del portátil:

   ```powershell
   ipconfig
   ```

4. **Firewall.**
   - En la demo no se abre nada: todo corre en la Pi, y el portátil solo sale hacia ella (el simulador y el navegador).
   - Para el plan B (paso 7), una persona del equipo, en PowerShell como administrador:

     ```powershell
     New-NetFirewallRule -DisplayName "AccesIA plan B" -Direction Inbound -Protocol TCP -LocalPort 1883,8000,8001 -RemoteAddress 192.168.137.0/24 -Action Allow
     ```

   - Para quitarla: `Remove-NetFirewallRule -DisplayName "AccesIA plan B"`.

**Se ve:** la zona encendida, con `AccesIA` en 2,4 GHz, y el adaptador «Conexión de área local*» del hotspot con `192.168.137.1` en `ipconfig`. Si es otra IP, se usa esa donde esta guía dice `192.168.137.1`.

## 2. La Pi en el hotspot, con la IP fija 192.168.137.250

Antes, en «Dispositivos conectados» de la zona, revisa que ningún equipo tenga ya la `.250`.

- **Si se puede entrar a Home Assistant** (con cable de red a una red con DHCP, o si el docente ya la conectó):
  1. Abre `http://homeassistant.local:8123`.
  2. Ve a Configuración → Sistema → Red → adaptador `wlan0` → Wi-Fi.
  3. Elige `AccesIA` y escribe su clave.
  4. En IPv4, elige «Estático» y pon:
     - dirección `192.168.137.250/24`;
     - puerta de enlace `192.168.137.1`;
     - DNS `192.168.137.1`.
  5. Guarda y quita el cable.
- **Si no hay cómo entrar:**
  1. Prepara una memoria USB llamada `CONFIG` (FAT32), con el archivo `network\my-network`, sin extensión.
  2. Conéctala a la Pi y reiníciala, o corre `ha os import` desde su consola.
  3. Después, borra el archivo de la memoria, porque lleva la clave del hotspot.

  Contenido de `my-network` (un GUID nuevo sale en PowerShell con `[guid]::NewGuid()`):

  ```ini
  [connection]
  id=my-network
  uuid=<un GUID nuevo>
  type=802-11-wireless

  [802-11-wireless]
  mode=infrastructure
  ssid=AccesIA

  [802-11-wireless-security]
  auth-alg=open
  key-mgmt=wpa-psk
  psk=<clave del hotspot>

  [ipv4]
  method=manual
  address1=192.168.137.250/24,192.168.137.1
  dns=192.168.137.1;

  [ipv6]
  addr-gen-mode=stable-privacy
  method=auto
  ```

**Se ve:**

- La Pi aparece en «Dispositivos conectados» con `192.168.137.250`.
- `ping 192.168.137.250` responde.
- `http://192.168.137.250:8123` abre Home Assistant.

Si la IP queda otra, se anota en `specs/arquitectura.md` (P-04) y se usa en el resto de la guía.

## 3. Terminar la configuración de Home Assistant y ver la RAM

1. Si Home Assistant es nuevo:
   - crea el usuario dueño, con credenciales del equipo que no van al repositorio;
   - pon Colombia, la zona horaria `America/Bogota`, el idioma español y el sistema métrico.

   Si ya estaba configurado, se revisa en Configuración → Sistema → General.
2. No actualices Home Assistant OS ni Core en clase, salvo que algo lo pida: tarda y necesita internet.
3. Mira la RAM en Configuración → Sistema → Hardware; después del paso 4 también sale con `free -h` en la terminal.
4. Anota si son 4 GB u 8 GB (P-04): decide el modelo de Ollama (paso 9).

**Se ve:** Home Assistant en español, con la hora de Colombia, y la RAM anotada.

## 4. Samba, SSH y Mosquitto

En Configuración → Complementos → Tienda de complementos:

1. **Samba share:**
   - Instalar.
   - En Configuración, pon un `username` y un `password`, que elige el equipo y no van al repositorio.
   - Iniciar.
   - En el Explorador de Windows, abre `\\192.168.137.250` con ese usuario.
2. **Terminal & SSH:** Instalar → Iniciar → «Abrir la interfaz web».
3. **Mosquitto broker**, como en `homeassistant/README.md` («Mosquitto»):
   1. En `\\192.168.137.250\share\mosquitto\`, copia `acl.conf` (de `homeassistant\mosquitto\`) y `accesscontrollist`.
      - `accesscontrollist` es la ACL de `contratos/mqtt.md` 1.4: `infra\mosquitto\acl` si ya dice «versión 1.4»; si no, el bloque del contrato.
      - Va con fin de línea LF.
   2. Instala el complemento. En Configuración → ⋮ → «Editar en YAML»:

      ```yaml
      logins:
        - username: servidor
          password: "<MQTT_SERVIDOR_CLAVE>"
        - username: camara
          password: "<MQTT_CAMARA_CLAVE>"
      require_certificate: false
      certfile: fullchain.pem
      keyfile: privkey.pem
      customize:
        active: true
        folder: mosquitto
      ```

   3. Inicia el complemento y acepta la integración MQTT que Home Assistant ofrece: Configurar → Enviar.

**Se ve:**

- En Windows, las carpetas `addons`, `backup`, `config`, `media`, `share` y `ssl`.
- En la terminal, `ha network info` muestra `192.168.137.250`.
- La integración MQTT aparece en Dispositivos y servicios, y el registro de Mosquitto no muestra errores.

## 5. Flashear la placa y configurarla por la consola

1. Conecta el módulo DHT: VCC a 3V3, DATA a D2 y GND a GND.
2. Flashea con el binario del C6 del kit de la sesión 1. Es la carpeta con `flash_args`, `bootloader\`, `partition_table\` y `accesia.bin`; hoy está en `firmware\build-c6`.
   - **Con ESP-IDF** (acceso directo «IDF_v5.4.4_Powershell»), desde la raíz del repositorio:

     ```powershell
     idf.py -C firmware -B firmware\build-c6 -p COM5 flash monitor
     ```

   - **Solo con esptool**, desde la carpeta del binario, y después un monitor serie a 115200:

     ```powershell
     python -m esptool --chip esp32c6 -p COM5 -b 460800 --before default_reset --after hard_reset write_flash "@flash_args"
     ```

   - El puerto sale en el Administrador de dispositivos como «Dispositivo serie USB». Si no conecta, mantén presionado BOOT mientras conectas el cable.
3. En el monitor:

   ```text
   wifi AccesIA <clave del hotspot>
   codigo entrada
   servidor http://192.168.137.250:8000
   mqtt mqtt://192.168.137.250:1883 camara <MQTT_CAMARA_CLAVE>
   sensor dht22
   antena interna
   estado
   reiniciar
   ```

   - Si el módulo es azul (DHT11), usa `sensor dht11`.
   - `antena externa` va solo con una antena en el U.FL.
   - El token se pone cuando la placa envíe recortes.
   - El código es el client id de MQTT: otro equipo con `entrada` la desconecta.

**Se ve:**

- El LED parpadea despacio mientras busca el Wi-Fi, rápido mientras llega al broker, y se apaga.
- `estado` muestra la IP, la señal y el broker conectado.
- La placa aparece en «Dispositivos conectados».

## 6. Temperatura y humedad, automatizaciones y panel «Portería»

1. **Temperatura y humedad (RF-14 · C4).** En Configuración → Dispositivos y servicios → MQTT aparece un dispositivo con Temperatura y Humedad (`sensor.accesia_entrada_temperatura` y `sensor.accesia_entrada_humedad`). No tiene nombre hasta que el servidor publique el suyo.
2. **La puerta a mano (RF-14 · C5).** En la integración MQTT → Configurar → Publicar un paquete, con el tema `accesia/entrada/puerta/set` y la carga `ABRIR`.
3. **Los archivos de Home Assistant,** como en `homeassistant/README.md` («Copiar los archivos a la Pi»):
   - por Samba, `automatizaciones_accesia.yaml` y `porteria.yaml` a `\\192.168.137.250\config\`;
   - las dos líneas de las automatizaciones y el bloque `lovelace:` en `configuration.yaml`;
   - «Comprobar configuración» y «Reiniciar».
4. **Las automatizaciones,** desde la raíz del repositorio en el portátil:

   ```powershell
   .\homeassistant\scripts\probar-automatizaciones.ps1
   ```

**Se ve:**

- Temperatura y humedad, con un valor nuevo cada 30 s.
- Con el paquete a mano, el LED encendido 3 s.
- En Automatizaciones, las dos de AccesIA; en la barra lateral, «Portería».
- El script dice «Bien: Home Assistant publicó ABRIR», y el LED se enciende 3 s.
- En la campana, «Desconocidos en entrada» con «3 caras desconocidas en 60 s, a las 08:15».
- El panel ya tiene temperatura, humedad, puerta y cámara en línea; lo demás llega con el servidor (paso 7). «Última persona» dice «Ana Gómez», el ejemplo del script, hasta el primer acceso real.

## 7. Nuestros complementos, si la B4 está lista, o el plan B

### Con la B4 en `main`

Como dice `specs/arquitectura.md` («Complementos de Home Assistant OS», Instalación). Construir necesita internet una vez: el del celular.

1. Haz `git pull` y arma `kit\complementos\` con el script de la B4.
2. Por Samba, copia las dos carpetas a `\\192.168.137.250\addons\`.
3. Tienda de complementos → ⋮ → «Buscar actualizaciones» → «Complementos locales»: instala `accesia_base` y `accesia_servidor`.
4. En sus opciones, pon las claves de `infra/.env` y las reglas.
5. Inicia primero la base y después el servidor.

**Se ve:**

- `curl.exe http://192.168.137.250:8000/api/v1/salud` responde con `"estado":"ok"`.
- La web abre en `http://192.168.137.250:8000`.
- En Home Assistant aparecen el dispositivo «AccesIA Servidor» y las entidades de la cámara, y el panel queda completo.

Después sigue el guion del Hito 2 (`tareas/dia-3/00-todos-orden-e-hito-2.md`).

### Sin la B4: plan B (escenario 2)

Así está en las specs (`specs/arquitectura.md`, «Red y despliegue»; `contratos/mqtt.md`, «Broker»): la base, el servidor y Mosquitto en el portátil; Home Assistant y Ollama en la Pi.

1. Crea la regla del firewall del paso 1.
2. Desde la carpeta principal:

   ```powershell
   docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml up -d --build
   curl.exe http://localhost:8000/api/v1/salud
   ```

3. En Home Assistant: integración MQTT → ⋮ → «Reconfigurar», con:
   - el broker `192.168.137.1` y el puerto `1883`;
   - el usuario `homeassistant` y la clave `MQTT_HA_CLAVE`.

   Detén el complemento Mosquitto de la Pi, para que no haya dos brokers.
4. En la consola de la placa:

   ```text
   servidor http://192.168.137.1:8000
   mqtt mqtt://192.168.137.1:1883 camara <MQTT_CAMARA_CLAVE>
   reiniciar
   ```

5. El agente usa `http://192.168.137.1:8001/mcp` (paso 9).

**Se ve:**

- La salud da `"estado":"ok"` en el portátil.
- En Home Assistant aparecen «AccesIA Servidor» y las entidades.
- La placa queda en línea.
- `.\homeassistant\scripts\probar-automatizaciones.ps1 -Broker 192.168.137.1` dice «Bien».

> **Pendiente de decisión.** Una variante dejaría el broker en la Pi y solo apuntaría el servidor del portátil a él (su `MQTT_URL`), sin reconfigurar Home Assistant ni la placa.
>
> No está en las specs: `contratos/mqtt.md` 1.4 dice que en el plan B el broker es el del portátil. Si el equipo la acepta, se anota en `decisiones.md` y en el contrato, y se suma su archivo de Compose antes de usarla.

## 8. Según el módulo de cámara que nos den (P-03)

Como dice `specs/arquitectura.md` («Cuando llegue el módulo de cámara»):

| Módulo | Qué se hace |
| --- | --- |
| Cámara SPI con JPEG para el C6 | No hay firmware para eso. El C6 enviaría el cuadro completo, y eso cambia `api-dispositivo.md` y `openapi.yaml` en su propio PR. En la demo sigue el simulador |
| Placa ESP32-S3 con cámara | Vuelve el firmware de referencia del PR #7, con su perfil (`esp32s3_eye`, `freenove_s3_cam`, `xiao_s3_sense` o los genéricos), y el contrato no cambia. Dos equipos no pueden usar el mismo código en MQTT: el código de la S3 y quién maneja la puerta se deciden con el frente A |
| ESP32-CAM | Cámara de respaldo con el modo extraer (`GET /capture`) y el binario `respaldo` del PR #7, si la B2 del Día 4 ya está en `main` |

En todos los casos, la cámara de la demo es el simulador hasta que el firmware nuevo esté probado:

```powershell
$env:TOKEN_CAMARA = "<token de la cámara entrada>"
uv run simulador webcam --codigo entrada --como-camara --servidor http://192.168.137.250:8000
```

El simulador va sin `--puerta`, porque la placa maneja la puerta de `entrada`.

## 9. Ollama y el agente, según la RAM

1. **El complemento de Ollama,** como en `homeassistant/README.md` («Ollama»):
   - por Samba, `kit\ollama\blobs` y `kit\ollama\manifests` a `\\192.168.137.250\share\ollama\`. Las otras dos carpetas del kit (`metadata` y `manifests-v2`) las crea Ollama solo;
   - el repositorio `https://github.com/SirUli/homeassistant-ollama-addon` y el complemento instalado;
   - `OLLAMA_FLASH_ATTENTION` en `1`, y el 11434 borrado en Red;
   - Iniciar.
2. **El modelo (D-22):**
   - con 4 GB, `qwen2.5:1.5b`;
   - con 8 GB, se miden `qwen2.5:1.5b` y `qwen2.5:3b` y se elige por las 10 preguntas y el tiempo;
   - con 2 GB o menos, escenario 2, y Ollama solo pasa al portátil con el visto bueno del profesor.
3. **La integración Ollama:** Añadir integración → Ollama → `http://<hash>-ollama:11434`, el nombre que sale en la pestaña Información del complemento.
4. **El agente,** según `contratos/mcp-agente.md` («Configuración en Home Assistant»):
   - las instrucciones;
   - la integración MCP: con la B4, `http://local-accesia-servidor:8001/mcp`; con el plan B, `http://192.168.137.1:8001/mcp`;
   - en «Herramientas de IA», solo AccesIA, y «Control de dispositivos» apagado (D-15);
   - el asistente «Portería» en español, y «Abrir puerta» sin exponer.

**Se ve:**

- La lista de modelos de la integración trae los dos del kit, sin bajar nada.
- En Assist, «¿Qué hora es?» responde con la hora de Colombia, y «Abre la puerta» responde que no puede.
- La primera pregunta después de arrancar Ollama tarda más (unos 45 s con 1.5b, estimado); las siguientes, mucho menos.
- Los tiempos se anotan en la bitácora (C2, paso 4).

Si una respuesta pasa de 15 s, primero se prueba en la Pi (RNF-03 · C3): las variantes Q4_0 (con internet), descripciones más cortas o `qwen2.5:0.5b`. Ollama pasa al portátil solo con el visto bueno del profesor.

## Planes B

| Si falla | Plan B |
| --- | --- |
| La cámara de la placa no está lista (D-21) | El simulador con la webcam del portátil; la placa sigue abriendo la puerta |
| La XIAO ESP32-C6 no conecta | El simulador con la webcam y `--puerta`, que también simula la puerta (A1) |
| La cámara deja de reconocer durante la demo | Registrar las llegadas a mano en la pantalla Asistencia (RF-06 · C5), cuando esté en `main` |
| Ollama va lento en la Raspberry | Primero, en la Raspberry: las variantes Q4_0, descripciones más cortas y `qwen2.5:0.5b` si responde bien (RNF-03 · C3). Ollama en el portátil, solo con el visto bueno del docente |
| La B4 no está lista, o la Raspberry no alcanza para la base y el servidor | Escenario 2 (paso 7) |
| No hay internet para instalar los complementos | El celular con datos; si tampoco hay, el escenario 2 |
| La Raspberry no arranca | Pedir una microSD al docente; si no hay, todo en el portátil con el mismo Compose |
| El hotspot del portátil no funciona | La red del salón o el hotspot del celular, reconfigurando la placa por consola |

## Qué preguntarle al docente (P-03 y P-04)

- Qué módulo de cámara llega y cómo se conecta: una cámara SPI para el C6 o una placa con cámara aparte.
- Si en el salón hay red con portal, o que aísle los equipos entre sí.
- Cuánta RAM tiene la Raspberry (D-22).
