<!--
Nombre: guia-dia-de-clase.md
Descripción: Guía para montar AccesIA el día de la clase, en orden y con lo que se debe ver en cada paso: hotspot, la Pi con Home Assistant OS, Mosquitto, la placa, los archivos de Home Assistant, los complementos o el plan B, la cámara y Ollama (D-21 y D-22).
Fecha de creación: 2026-11-11
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 2.1
-->

# Guía del día de clase

Meta: pasar de las cajas cerradas a la primera persona reconocida en menos de 45 minutos, sin depender del internet de la universidad.

El hardware ya se conoce (D-21): una Seeed Studio XIAO ESP32-C6 y una Raspberry Pi 5 con Home Assistant OS. En la demo todo corre en la Pi, como complementos de Home Assistant OS, en el hotspot de Windows del portátil (D-22). El escenario 2, con la base y el servidor en el portátil y el broker en la Pi (D-23), queda como plan B.

- **Las claves:** salen de `infra/.env` del portátil y no se escriben en el repositorio ni en esta guía.
- **«Se ve»:** cada paso termina con lo que se debe ver. Si no se ve, no se sigue: se arregla primero.
- **Los detalles de Home Assistant:** cada complemento y cada archivo están en `homeassistant/README.md`.

## Antes de salir

- [ ] El repositorio en `main`, con `infra/.env` y las claves de MQTT del Día 1.
- [ ] `kit\` en la carpeta principal, que Git ignora. En clase se usa solo esta carpeta:
  - [ ] `kit\complementos\`: `accesia_base` y `accesia_servidor`, con los modelos de cara (D-22). Se arma con `.\scripts\empaquetar-complementos.ps1`, y se vuelve a armar después de cada `git pull` que cambie el servidor.
  - [ ] `kit\firmware\`: el binario de la XIAO ESP32-C6 y, por si llega un ESP32-S3, los binarios octal y quad del PR #7, con `flashear.ps1`. Se arma con `.\firmware\scripts\armar-kit.ps1`, y `c6\origen.txt` dice de qué commit sale.
  - [ ] `kit\ollama\`: 2,8 GB, con `qwen2.5:1.5b` y `qwen2.5:3b`, para `/share/ollama` sin internet (`homeassistant/README.md`, «El kit de Ollama»).
- [ ] ESP-IDF 5.4.4 en el portátil: `flashear.ps1` usa su esptool si no hay otro en el PATH.
- [ ] Docker Desktop con las imágenes del plan B ya construidas (`docker compose -f infra/compose.yaml up -d --build` una vez) y `eclipse-mosquitto:2`, que usa el script de prueba.
- [ ] El hotspot ya configurado (paso 1).
- [ ] El celular con datos: el portátil necesita una conexión para encender el hotspot, y los complementos, internet para instalarse.
- [ ] El cable USB-C de datos, el módulo DHT y sus cables, un cable de red y una memoria USB (paso 2).

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
   - Para el plan B (paso 7), una persona del equipo, en PowerShell como administrador, deja entrar el 8001 del MCP solo desde el hotspot:

     ```powershell
     New-NetFirewallRule -DisplayName "AccesIA plan B" -Direction Inbound -Protocol TCP -LocalPort 8001 -RemoteAddress 192.168.137.0/24 -Action Allow
     ```

   - Si el broker vuelve al portátil (paso 7, «Si la Pi no tiene Mosquitto»), suma el 1883: `Set-NetFirewallRule -DisplayName "AccesIA plan B" -LocalPort 1883,8001`.
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

Si la IP queda otra, se anota en `specs/arquitectura.md` (P-04) y se usa en el resto de la guía; para el plan B, también en `IP_DE_LA_PI` (paso 7).

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
      - `accesscontrollist` es una copia de `infra\mosquitto\acl`, la ACL de `contratos/mqtt.md`.
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
2. Flashea con el kit, desde la carpeta principal:

   ```powershell
   .\kit\firmware\flashear.ps1 -Placa c6 -Puerto COM5
   ```

   - El puerto sale en el Administrador de dispositivos como «Dispositivo serie USB». Sin `-Puerto`, esptool busca la placa.
   - El script dice cómo poner la placa en modo de descarga, flashea y muestra los comandos de la consola que faltan.
   - Usa el esptool del PATH o el de ESP-IDF 5.4. Con `-WhatIf` muestra el comando sin flashear.
   - Al volver a flashear, la configuración de la consola se conserva; `-Borrar` la borra con toda la flash.
3. Abre la consola a 115200 baudios: `python -m serial.tools.miniterm COM5 115200`, con el Python de ESP-IDF, o `idf.py -C firmware -B firmware\build-c6 -p COM5 monitor` si el firmware está compilado. Escribe:

   ```text
   wifi AccesIA <clave del hotspot>
   codigo entrada
   mqtt mqtt://192.168.137.250:1883 camara <MQTT_CAMARA_CLAVE>
   estado
   reiniciar
   ```

   - Los valores de fábrica ya apuntan a la Pi (`192.168.137.250`, D-22), con la puerta en el LED, DHT22 y la antena interna. Si la Pi quedó en otra IP, también `servidor http://<IP>:8000` y `mqtt` con esa IP.
   - Si el módulo es azul (DHT11), usa `sensor dht11`. `antena externa` va solo con una antena en el U.FL.
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

## 7. Nuestros complementos o el plan B

### Nuestros complementos (B4)

La B4 está en `main` desde el PR #26. Se instalan como dice `complementos/README.md` («Instalar en la Pi»); el Mosquitto ya quedó en el paso 4. Construir necesita internet una vez: el del celular.

1. Por Samba, copia `kit\complementos\accesia_base` y `kit\complementos\accesia_servidor` a `\\192.168.137.250\addons\`.
2. Tienda de complementos → ⋮ → «Buscar actualizaciones» → «Complementos locales»: instala «AccesIA · base de datos» y «AccesIA · servidor». La Pi construye cada imagen.
3. «AccesIA · base de datos»: pon `clave_base`, la `POSTGRES_PASSWORD` de `infra\.env`, e inícialo.
4. «AccesIA · servidor»: pon sus opciones con las claves de `infra\.env` (la lista está en `complementos/accesia_servidor/DOCS.md`), enciende el Watchdog e inícialo.
5. En la web, en Cámaras, crea la cámara `entrada`. Su token sale una sola vez.

**Se ve:**

- El registro del servidor dice que corrió la migración.
- `curl.exe http://192.168.137.250:8000/api/v1/salud` responde con `"estado":"ok"`.
- La web abre en `http://192.168.137.250:8000/`.
- En Home Assistant aparecen el dispositivo «AccesIA Servidor» y las entidades de la cámara, y el panel queda completo.

Después sigue el guion del Hito 2 (`tareas/dia-3/00-todos-orden-e-hito-2.md`).

### Si no se pueden instalar: plan B (escenario 2, D-23)

La base, el servidor y el MCP corren en el portátil, y Home Assistant, Mosquitto y Ollama siguen en la Pi. El servidor del portátil usa el broker de la Pi, así que Home Assistant y la placa no se tocan.

1. Crea la regla del firewall del paso 1.
2. Desde la carpeta principal, con las imágenes ya construidas:

   ```powershell
   docker compose -f infra/compose.yaml down
   docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml -f infra/compose.broker-pi.yaml up -d
   curl.exe http://localhost:8000/api/v1/salud
   ```

   Si la Pi quedó en otra IP, antes del `up`: `$env:IP_DE_LA_PI = "<IP de la Pi>"`.
3. En la web del portátil, `http://localhost:8000`, la cámara `entrada` ya existe. En Cámaras → `entrada` → «Cambiar token», el token nuevo sale una sola vez. Es para el simulador, que en el plan B va sin `--servidor`, porque el servidor es el del portátil.
4. El agente usa `http://192.168.137.1:8001/mcp` (paso 9).

**Se ve:**

- `docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml -f infra/compose.broker-pi.yaml ps` muestra `postgres`, `servidor` y `mcp` sanos, sin `mosquitto`.
- La salud responde `"mqtt":"ok"` y `"estado":"ok"`.
- En Home Assistant aparecen «AccesIA Servidor» y las entidades de la cámara, sin tocar la integración MQTT.
- `.\homeassistant\scripts\probar-automatizaciones.ps1` sigue diciendo «Bien».

**Si la Pi no tiene Mosquitto** (por ejemplo, porque no hubo internet para instalarlo), el broker vuelve al portátil, como antes de D-23:

1. Suma el 1883 a la regla del firewall (paso 1).
2. Levanta sin `compose.broker-pi.yaml`: `docker compose -f infra/compose.yaml -f infra/compose.escenario2.yaml up -d`.
3. En Home Assistant: Añadir integración → MQTT, con el broker `192.168.137.1`, el puerto `1883`, el usuario `homeassistant` y la clave `MQTT_HA_CLAVE`.
4. En la consola de la placa: `mqtt mqtt://192.168.137.1:1883 camara <MQTT_CAMARA_CLAVE>` y `reiniciar`.
5. Prueba las automatizaciones con `.\homeassistant\scripts\probar-automatizaciones.ps1 -Broker 192.168.137.1`.

## 8. Según el módulo de cámara que nos den (P-03)

Como dice `specs/arquitectura.md` («Cuando llegue el módulo de cámara»):

| Módulo | Qué se hace |
| --- | --- |
| Cámara SPI con JPEG para el C6 | No hay firmware para eso. El C6 enviaría el cuadro completo, y eso cambia `api-dispositivo.md` y `openapi.yaml` en su propio PR. En la demo sigue el simulador |
| Placa ESP32-S3 con cámara | Vuelve el firmware de referencia del PR #7, que está en el kit: `.\kit\firmware\flashear.ps1 -Detectar` dice si su PSRAM es octal o quad; después se flashea con `-Placa s3-octal` o `-Placa s3-quad`, y por consola se elige su `perfil` (`esp32s3_eye`, `freenove_s3_cam`, `xiao_s3_sense` o los genéricos). El contrato no cambia. Dos equipos no pueden usar el mismo código en MQTT: el código de la S3 y quién maneja la puerta se deciden con el frente A |
| ESP32-CAM, o un celular con una aplicación de cámara IP | Cámara de respaldo con el modo extraer (B2 del Día 4): el servidor le pide una foto por segundo por HTTP, sin tocar su firmware (RF-10 · C4). Se registra con su URL de captura, como dice `servidor/README.md` («Registrar una cámara de respaldo, paso a paso») |

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
| La cámara de la placa no está lista (D-21) | El simulador con la webcam del portátil, con `--servidor http://192.168.137.250:8000`; la placa sigue abriendo la puerta |
| Llega un ESP32-CAM, o un celular hace de cámara | Cámara de respaldo con el modo extraer (paso 8) |
| La XIAO ESP32-C6 no conecta | El simulador con la webcam y `--puerta`, que también simula la puerta (A1) |
| La cámara deja de reconocer durante la demo | Registrar las llegadas a mano en la pantalla Asistencia (RF-06 · C5), cuando esté en `main` |
| Ollama va lento en la Raspberry | Primero, en la Raspberry: las variantes Q4_0, descripciones más cortas, `qwen2.5:0.5b` si responde bien y el comienzo del prompt estable (RNF-03 · C3). Ollama en el portátil, solo con el visto bueno del docente |
| Los complementos no se instalan, o la Raspberry no alcanza para la base y el servidor | Escenario 2, con el broker de la Pi (paso 7, D-23) |
| No hay internet para instalar los complementos | El celular con datos; si tampoco hay, el escenario 2, y sin Mosquitto en la Pi, con el broker del portátil (paso 7) |
| La Raspberry no arranca | Pedir una microSD al docente; si no hay, todo en el portátil con el mismo Compose |
| El hotspot del portátil no funciona | La red del salón o el hotspot del celular, reconfigurando la placa por consola |

## Qué preguntarle al docente (P-03 y P-04)

- Qué módulo de cámara llega y cómo se conecta: una cámara SPI para el C6 o una placa con cámara aparte.
- Si en el salón hay red con portal, o que aísle los equipos entre sí.
- Cuánta RAM tiene la Raspberry (D-22).
