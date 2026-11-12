<!--
Nombre: README.md
Descripción: Firmware de la placa XIAO ESP32-C6 de AccesIA (frente A): instalación, compilar, flashear, consola, prueba con la placa y pruebas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Firmware de la placa · frente A

Firmware de la Seeed Studio XIAO ESP32-C6 en ESP-IDF 5.4 (C++), en un solo binario (D-21). Se conecta al hotspot del portátil y por MQTT:

- abre la puerta (el LED de GPIO15) cuando Home Assistant lo pide;
- publica el estado de la puerta, su estado general y su disponibilidad;
- cada 30 s lee un sensor DHT22 o DHT11 y publica la temperatura y la humedad, con el descubrimiento de los dos sensores para Home Assistant.

La placa todavía no tiene cámara: llega la próxima clase (P-03), y hasta entonces la cámara es el simulador.

- Specs: `specs/arquitectura.md` (Firmware), `specs/requisitos.md` (RF-14) y el contrato `specs/contratos/mqtt.md` 1.2.
- El firmware del ESP32-S3 del enunciado, con la detección de caras, queda como referencia en el PR #7. Puede volver como otro target de este mismo proyecto.

## Instalar ESP-IDF 5.4.4 (una vez)

Se instala con EIM (ESP-IDF Installation Manager), el instalador oficial de Espressif. Es el mismo que usa la extensión ESP-IDF de VS Code, así que la extensión encuentra la instalación sin configurar nada.

- Con VS Code: instala la extensión «ESP-IDF» de Espressif, corre `ESP-IDF: Open ESP-IDF Installation Manager` y elige v5.4.4 y `esp32c6`.
- Por línea de comandos, con `eim-cli-windows-x64.exe` de [github.com/espressif/idf-im-ui/releases](https://github.com/espressif/idf-im-ui/releases) o con `winget install Espressif.EIM-CLI`:

```powershell
eim install -i v5.4.4 -t esp32c6 -p C:\esp -n true --do-not-track true
```

La instalación del Día 1, hecha para el `esp32s3`, también sirve para el C6, porque trae la misma cadena RISC-V (`riscv32-esp-elf`).

Queda así:

- ESP-IDF en `C:\esp\v5.4.4\esp-idf` y sus herramientas en `C:\Espressif\tools`. Esas rutas no pueden tener espacios.
- Un acceso directo «IDF_v5.4.4_Powershell» en el escritorio, que abre PowerShell con ESP-IDF activado.
- `C:\Espressif\tools\eim_idf.json`, donde la extensión de VS Code y `compilar.ps1` encuentran la instalación.

ESP-IDF se usa desde PowerShell, no desde Git Bash: `idf.py` no funciona en MSYS. La ruta del repositorio sí puede tener espacios («Inteligencia artificial»): con ESP-IDF 5.4.4 compila bien.

## Compilar

Desde la raíz del repositorio, en PowerShell:

```powershell
.\firmware\scripts\compilar.ps1
```

- Compila para el `esp32c6` en `firmware\build-c6`, con su `sdkconfig` dentro de esa carpeta. Git ignora `build-*/`, `sdkconfig` y `managed_components/`.
- Si `idf.py` no está a mano, el script activa ESP-IDF 5.4 con lo que dejó EIM en `eim_idf.json`.
- Usa `sdkconfig.defaults` más `sdkconfig.defaults.esp32c6`, que ESP-IDF suma solo según el target.
- La primera vez baja las dependencias del ESP Component Registry y tarda unos minutos; después, ccache acelera.
- En VS Code, elige el target `esp32c6` con `ESP-IDF: Set Espressif Device Target` antes de usar el botón de compilar.

| Binario | Tamaño | Partición `factory` |
| --- | --- | --- |
| `firmware\build-c6\accesia.bin` | 1,05 MB | el 34 % de 3 MB |

La tabla de particiones (`particiones.csv`) cabe en los 4 MB de flash de la XIAO.

## Flashear

Desde el acceso directo «IDF_v5.4.4_Powershell» o la terminal de ESP-IDF en VS Code, con la placa conectada por el USB-C. El puerto (`COM5` en el ejemplo) aparece en el Administrador de dispositivos como «Dispositivo serie USB».

```powershell
idf.py -C firmware -B firmware\build-c6 -p COM5 flash monitor
```

- `Ctrl+]` sale del monitor.
- Si no conecta, mantén presionado BOOT mientras conectas el cable y vuelve a intentar.

## Consola

Los comandos entran por el USB-C (USB Serial/JTAG) y por UART0 (GPIO16 y GPIO17). Se guardan en NVS: no hace falta recompilar (RF-14 · C6).

| Comando | Ejemplo |
| --- | --- |
| `estado` | Muestra la placa, el Wi-Fi, la IP y la señal, el servidor, MQTT, la puerta, el sensor con su última lectura y la antena |
| `wifi <ssid> <clave>` | `wifi AccesIA clave123`; si el nombre tiene espacios, va entre comillas |
| `servidor <url>` | `servidor http://192.168.137.1:8000` |
| `codigo <codigo>` | `codigo entrada`; de 3 a 32 letras minúsculas, números o guiones, y no `servidor` |
| `token <token>` | El token que da la web al crear la cámara |
| `mqtt <url> <usuario> <clave>` | `mqtt mqtt://192.168.137.1:1883 camara clave123` |
| `puerta <pin> <segundos> [bajo\|alto]` | `puerta 15 3 bajo`, lo de fábrica. El nivel es el que enciende; `-1` si no hay LED ni relé; de 1 a 60 s |
| `sensor <dht22\|dht11>` | `sensor dht11` |
| `antena <interna\|externa>` | `antena externa`, con una antena en el conector U.FL |
| `reiniciar` | Reinicia la placa |
| `ayuda` | Lista los comandos |

- Valores de fábrica (`arquitectura.md`): Wi-Fi «AccesIA», servidor `http://192.168.137.1:8000`, MQTT `mqtt://192.168.137.1:1883` con el usuario `camara`, la puerta en el LED (GPIO15, 3 s, enciende en bajo), DHT22 y la antena interna.
- `estado` no muestra las claves ni el token. Quedan en la placa sin cifrar.
- `puerta` rechaza los pines que la placa ya usa: la flash (GPIO24 a GPIO30), el USB (12 y 13), UART0 (16 y 17), el sensor (2), la antena (3 y 14) y BOOT (9).
- `codigo` borra antes el descubrimiento de sus dos sensores, porque con el código nuevo la ACL ya no la deja.
- Cómo funciona: la consola de ESP-IDF tiene UART0 como principal y el USB nativo como secundario, y el secundario solo envía texto. Por eso dos tareas propias leen los comandos de los dos puertos y los pasan a `esp_console_run`.

## Qué hace

| Pin | Uso |
| --- | --- |
| D2 = GPIO2 | DATA del sensor DHT22 o DHT11 |
| GPIO3 | Conmutador de antena: en bajo al arrancar, antes del Wi-Fi |
| GPIO14 | Antena: en bajo la interna, en alto la externa (U.FL) |
| GPIO15 | LED de usuario, que enciende en bajo: la puerta y el estado de la placa |

- Al arrancar enciende el conmutador de antena y elige la antena (RF-14 · C2). Después se conecta al Wi-Fi, con reintentos de 1, 2, 4, 8 y 10 s, y a MQTT con su código como client id (la ACL lo exige).
- MQTT (`specs/contratos/mqtt.md`):
  - se suscribe a `accesia/{codigo}/puerta/set`;
  - al conectarse publica `online` en `accesia/{codigo}/disponible`, el descubrimiento de sus dos sensores, el estado de la puerta y su estado general;
  - el estado general sale de nuevo cada 60 s; el último deseo publica `offline`.
- Ambiente (RF-14 · C3): cada 30 s publica `{"temperatura": 24.6, "humedad": 58.0}` en `accesia/{codigo}/ambiente`, retenido. Una lectura fuera del rango del sensor cuenta como falla, y desde la tercera falla seguida publica `null` en los dos campos.
- Puerta (RF-14 · C5): con `ABRIR` enciende el LED los segundos configurados y publica `abierta` y luego `cerrada`. Un `ABRIR` con la puerta abierta vuelve a contar; `CERRAR` la cierra antes.
- El resto del tiempo el LED muestra el estado: parpadea despacio (cada 500 ms) sin Wi-Fi, rápido (cada 150 ms) sin broker y queda apagado con todo conectado.

## Prueba con la placa

Así se prueba la placa con el broker y Home Assistant de la demo (escenario 2, D-21). Para el portátil son los pasos 1 a 3; el 4 es en la Raspberry y el 5, en la placa.

### 1. Hotspot del portátil

En Windows 11, en Configuración → Red e Internet → Zona con cobertura inalámbrica móvil → Propiedades → Editar:

- Nombre: `AccesIA`.
- Contraseña: la del equipo, de 8 a 63 caracteres. No va en el repositorio.
- Banda de red: 2,4 GHz, porque el C6 no usa 5 GHz.

Enciende la zona. Windows solo la enciende si el portátil tiene una conexión que compartir (Wi-Fi, cable o el celular). Comprueba la IP del portátil:

```powershell
ipconfig
```

El adaptador «Conexión de área local*» del hotspot suele tener `192.168.137.1`. Si es otra, úsala en lugar de `192.168.137.1` en los pasos siguientes. La lista «Dispositivos conectados» de la zona muestra la IP de la placa y la de la Raspberry.

### 2. Firewall de Windows

Una vez, en PowerShell como administrador:

```powershell
New-NetFirewallRule -DisplayName "AccesIA en el hotspot" -Direction Inbound -Protocol TCP -LocalPort 1883,8001,11434 -RemoteAddress 192.168.137.0/24 -Action Allow
```

- Deja entrar solo desde la red del hotspot el 1883 (MQTT, para la placa y Home Assistant) y los puertos que usa la Raspberry: el 8001 (`mcp`) y el 11434 (`ollama`). Para esta prueba basta el 1883.
- Para quitarla: `Remove-NetFirewallRule -DisplayName "AccesIA en el hotspot"`.

### 3. Broker en el portátil

El broker es el Mosquitto del compose. Su ACL (`infra/mosquitto/acl`) ya deja que la placa publique su ambiente y el descubrimiento de sus sensores. Desde la raíz del repositorio, con Docker Desktop abierto:

```powershell
.\infra\scripts\generar-env.ps1                      # una vez: crea infra/.env con claves nuevas
.\infra\scripts\crear-claves-mqtt.ps1                # una vez: los usuarios servidor, homeassistant y camara
docker compose -f infra/compose.yaml up -d mosquitto # solo el broker; sin el nombre, levanta todo
```

- Mosquitto publica el 1883 en todas las interfaces del portátil, también en la del hotspot. `compose.escenario2.yaml`, que sumará `mcp` y `ollama` para la Raspberry, todavía no existe.
- Si el broker ya corría con la ACL anterior, reinícialo para que lea la nueva: `docker compose -f infra/compose.yaml restart mosquitto`.
- Si otra copia del repositorio (otro worktree) tiene el compose levantado, bájala antes: usan los mismos nombres y puertos.
- Para ver lo que publica la placa, con la clave `MQTT_SERVIDOR_CLAVE` de `infra/.env`:

```powershell
docker compose -f infra/compose.yaml exec mosquitto mosquitto_sub -u servidor -P "<MQTT_SERVIDOR_CLAVE>" -t "accesia/#" -t "homeassistant/sensor/#" -v
```

### 4. Integración MQTT de Home Assistant

En la Raspberry Pi 5 con Home Assistant OS:

1. Conéctala al hotspot: Ajustes → Sistema → Red, en la interfaz `wlan0`, la red `AccesIA`. Después se abre en `http://<IP de la Raspberry>:8123`.
2. Ajustes → Dispositivos y servicios → Añadir integración → MQTT:
   - broker `192.168.137.1` y puerto `1883`;
   - usuario `homeassistant` y la clave `MQTT_HA_CLAVE` de `infra/.env`;
   - el descubrimiento queda activo con el prefijo `homeassistant`, como viene.
3. No instales el complemento Mosquitto de Home Assistant: el broker es el del portátil (D-21).

### 5. La placa, por la consola

Conecta el módulo DHT de tres pines: VCC a 3V3, DATA a D2 y GND a GND. El módulo trae su resistencia de pull-up.

Flashea la placa (ver «Flashear») y escribe en el monitor:

```text
wifi AccesIA <clave del hotspot>
codigo entrada
mqtt mqtt://192.168.137.1:1883 camara <MQTT_CAMARA_CLAVE>
sensor dht22
antena interna
estado
reiniciar
```

- `sensor dht11` si el módulo es un DHT11 (suele ser azul; el DHT22, blanco). `antena externa` solo con una antena en el U.FL.
- El servidor y la puerta ya tienen sus valores de fábrica. El token lo usará la placa cuando envíe recortes; para esta prueba no hace falta.
- El código es el client id de MQTT: el simulador no puede estar conectado a la vez con el mismo código.

### Qué comprobar

| Criterio | Cómo se ve |
| --- | --- |
| Conexión | El LED parpadea despacio mientras busca el Wi-Fi, rápido mientras llega al broker, y se apaga. `estado` muestra la IP, la señal y el broker conectado; `accesia/entrada/disponible` queda en `online` |
| RF-14 · C2 | `estado` muestra la antena. Con `antena externa`, `reiniciar` y una antena en el U.FL, cambia la señal |
| RF-14 · C3 | Cada 30 s llega `accesia/entrada/ambiente` con la temperatura y la humedad. Con el DATA desconectado, desde la tercera lectura (unos 90 s) llega `null` |
| RF-14 · C4 | En Home Assistant aparece un dispositivo con Temperatura y Humedad (`sensor.accesia_entrada_temperatura` y `sensor.accesia_entrada_humedad`), aunque el servidor esté apagado. Sin nombre: el nombre y el modelo los pone el servidor. Con `null`, los sensores quedan en desconocido. Al desconectar la placa, en unos 45 s el broker publica `offline` y quedan no disponibles |
| RF-14 · C5 | En Home Assistant, en la integración MQTT → Configurar → Publicar un paquete: tema `accesia/entrada/puerta/set` y carga `ABRIR`. El LED se enciende 3 s y `accesia/entrada/puerta/estado` pasa a `abierta` y luego a `cerrada` |
| RF-14 · C6 | Todo lo anterior se configuró por consola, sin recompilar |

### Si algo falla

| Qué pasa | Qué revisar |
| --- | --- |
| La placa no ve la red | La banda de 2,4 GHz, el nombre y la clave. Si el portátil está conectado a una red de 5 GHz, algunas tarjetas solo ofrecen el hotspot en esa banda: conéctalo por cable, al celular o a una red de 2,4 GHz |
| El LED sigue parpadeando rápido | Que el broker corra (`docker compose -f infra/compose.yaml ps`), la regla del firewall, la IP del portátil y la clave de `camara`, y que no haya otro cliente con el mismo código. Una regla de bloqueo gana sobre una de permitir: revisa que ninguna bloquee a Docker Desktop en esa red |
| Home Assistant no muestra los sensores | Que la integración MQTT esté conectada al broker del portátil y que el broker se haya reiniciado con la ACL nueva. Con `mosquitto_sub` se ven los dos `config` en `homeassistant/sensor/entrada/…` |
| Temperatura y humedad en desconocido | El cableado (DATA a D2) y el tipo de sensor (`sensor dht22` o `sensor dht11`) |
| Una placa retirada deja sus sensores en Home Assistant | Borra sus dos `config` retenidos, como en «Pruebas» de `specs/contratos/mqtt.md` |

## Pruebas de la lógica pura

```powershell
.\firmware\scripts\probar-logica.ps1
```

- Corren en un contenedor `ubuntu:24.04` de Docker Desktop, que se borra al terminar. El contenedor instala g++, CMake y Ninja y compila `firmware/pruebas/` con doctest 2.5.3 y nlohmann/json 3.12.0, que se descargan comprobando su huella SHA-256.
- Prueban los mismos archivos que compila ESP-IDF, los de `components/accesia_logica` y `components/accesia_recorte`:
  - los mensajes MQTT de la placa, como en el contrato (`contrato MQTT · ambiente`, `contrato MQTT · descubrimiento de la placa` y `contrato MQTT · estado`);
  - la antena y los pines que acepta `puerta` (`RF-14 · C2` y `RF-14 · C6`);
  - las lecturas, los rangos de cada sensor y el `null` tras 3 fallas (`RF-14 · C3`);
  - la puerta y el LED (`RF-14 · C5`);
  - el recorte, para cuando llegue la cámara (`contrato recorte · <caso>`, `RF-01 · C2`, `RF-01 · C3` y `contrato cámara · espera 3 s`).
- Corren con el detector de comportamiento indefinido de GCC, y con `-Werror`.
- En Linux, sin Docker: `bash firmware/scripts/probar-logica.sh`.
- GitHub Actions (`.github/workflows/firmware.yml`) compila el firmware con la imagen `espressif/idf:v5.4.4` y corre estas pruebas en cada PR (RF-14 · C1). También revisa que `dependencies.lock.esp32c6` esté al día.

## Dependencias

Las versiones están fijas en `main/idf_component.yml`, solo para el `esp32c6`. `dependencies.lock.esp32c6`, en Git, fija también las dependencias de esas dependencias; cada target tiene su propio lockfile.

| Componente | Versión | Por qué esa |
| --- | --- | --- |
| `esp-idf-lib/dht` | 1.2.0 | Lee el DHT22 y el DHT11 y declara soporte para el `esp32c6`. Reemplaza a ESPHome |
| `esp-idf-lib/esp_idf_lib_helpers` | 1.4.0 | `dht` la pide sin versión; se fija aquí |

## Estructura

```text
firmware/
├── CMakeLists.txt              proyecto ESP-IDF (versión 0.2.0); target esp32c6 por defecto y un lockfile por target
├── sdkconfig.defaults          común: rendimiento, flash de 4 MB, particiones y consola
├── sdkconfig.defaults.esp32c6  160 MHz
├── particiones.csv             nvs, phy_init y factory de 3 MB
├── dependencies.lock.esp32c6   versiones exactas de las dependencias del C6
├── main/                       arranque; idf_component.yml con las versiones
├── components/
│   ├── accesia_config/         configuración en NVS
│   ├── accesia_consola/        consola por UART0 y por el USB nativo
│   ├── accesia_red/            Wi-Fi, IP y señal
│   ├── accesia_mqtt/           temas, descubrimiento, último deseo y estado general
│   ├── accesia_puerta/         la puerta en el LED o en un relé
│   ├── accesia_ambiente/       sensor DHT (solo C6)
│   ├── accesia_placa_c6/       antena, LED y pines de la XIAO ESP32-C6 (solo C6)
│   ├── accesia_logica/         lógica pura: mensajes, puerta, ambiente, LED y pines
│   ├── accesia_recorte/        lógica pura del recorte y la espera, para la cámara
│   └── accesia_vision/         punto de extensión de la cámara: fuente de cuadros y detector
├── pruebas/                    pruebas de la lógica pura (CMake y doctest)
└── scripts/                    compilar.ps1, probar-logica.ps1 y probar-logica.sh
```

`accesia_vision` solo tiene interfaces. Qué las implementa depende del módulo de cámara que llegue: lo cuenta `arquitectura.md`, en «Cuando llegue el módulo de cámara».

## Por verificar con la placa

- Que el LED de GPIO15 encienda en bajo: la wiki de Seeed no lo dice.
- El conmutador y la selección de antena (GPIO3 y GPIO14), y la señal con cada antena.
- Que los comandos entren por el USB-C y por UART0.
- Las lecturas del DHT22 y del DHT11 en GPIO2 con 3V3.
- Que la placa y Home Assistant lleguen al broker del portátil por el hotspot, con la regla del firewall.
