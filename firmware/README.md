<!--
Nombre: README.md
Descripción: Firmware de AccesIA (frente A): la ESP32-CAM de la demo (D-24) y, como referencia, la XIAO ESP32-C6. Instalación, compilar, flashear, consola, prueba con la placa y pruebas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 1.4
-->

# Firmware de la placa · frente A

Firmware de la ESP32-CAM AI-Thinker en ESP-IDF 5.4 (C++), en un solo binario (D-24). La placa hace de cámara y de punto de acceso:

- detecta caras con ESP-DL 1.1 (`HumanFaceDetectMSR01` + `MNP01`, P-05), recorta la más grande y la envía al servidor (`api-dispositivo.md` 1.2);
- publica por MQTT su presencia, su estado y su disponibilidad (`mqtt.md` 1.6);
- abre la puerta (el LED rojo, GPIO33) cuando Home Assistant lo pide.

El mismo proyecto compila para la XIAO ESP32-C6 de D-21, que ya no se usa: puerta, estado y un sensor DHT. El firmware del ESP32-S3 del enunciado queda de respaldo en el PR #7.

- Specs: `specs/arquitectura.md` (Firmware), `specs/requisitos.md` (RF-01) y los contratos `api-dispositivo.md` 1.2 y `mqtt.md` 1.6.

## Instalar ESP-IDF 5.4.4 (una vez)

Se instala con EIM (ESP-IDF Installation Manager), el instalador oficial de Espressif. Es el mismo que usa la extensión ESP-IDF de VS Code, así que la extensión encuentra la instalación sin configurar nada.

- Con VS Code: instala la extensión «ESP-IDF» de Espressif, corre `ESP-IDF: Open ESP-IDF Installation Manager` y elige v5.4.4, con `esp32` (y `esp32c6` si hace falta el C6).
- Por línea de comandos, con `eim-cli-windows-x64.exe` de [github.com/espressif/idf-im-ui/releases](https://github.com/espressif/idf-im-ui/releases) o con `winget install Espressif.EIM-CLI`:

```powershell
eim install -i v5.4.4 -t esp32,esp32c6 -p C:\esp -n true --do-not-track true
```

La instalación del Día 1, hecha para el `esp32s3`, también sirve para el `esp32`, porque trae la misma cadena Xtensa (`xtensa-esp-elf`).

Queda así:

- ESP-IDF en `C:\esp\v5.4.4\esp-idf` y sus herramientas en `C:\Espressif\tools`. Esas rutas no pueden tener espacios.
- Un acceso directo «IDF_v5.4.4_Powershell» en el escritorio, que abre PowerShell con ESP-IDF activado.
- `C:\Espressif\tools\eim_idf.json`, donde la extensión de VS Code y los scripts encuentran la instalación.

ESP-IDF se usa desde PowerShell, no desde Git Bash: `idf.py` no funciona en MSYS. La ruta del repositorio sí puede tener espacios («Inteligencia artificial»). ESP-DL 1.1 no lo resolvía bien al enlazar, y `CMakeLists.txt` lo corrige.

## Compilar

Desde la raíz del repositorio, en PowerShell:

```powershell
.\firmware\scripts\compilar.ps1                      # la ESP32-CAM, en firmware\build-esp32cam
.\firmware\scripts\compilar.ps1 -Placa esp32cam, c6  # también la XIAO ESP32-C6, en firmware\build-c6
```

- Cada placa compila con su target (`esp32` o `esp32c6`) en su carpeta, con su `sdkconfig` dentro. Git ignora `build-*/`, `sdkconfig` y `managed_components/`.
- Si `idf.py` no está a mano, el script activa ESP-IDF 5.4 con lo que dejó EIM en `eim_idf.json`.
- Usa `sdkconfig.defaults` más `sdkconfig.defaults.<target>`, que ESP-IDF suma solo.
- La primera vez baja las dependencias del ESP Component Registry y tarda unos minutos; después, ccache acelera.
- En VS Code, elige el target con `ESP-IDF: Set Espressif Device Target` antes de usar el botón de compilar. Sin elegir, es `esp32`.

| Binario | Tamaño | Partición `factory` |
| --- | --- | --- |
| `firmware\build-esp32cam\accesia.bin` | 1,70 MB | el 54 % de 3 MB |
| `firmware\build-c6\accesia.bin` | 1,06 MB | el 34 % de 3 MB |

En la ESP32-CAM, la IRAM queda al 97 %. Si un cambio la desborda, `CONFIG_ESP_WIFI_IRAM_OPT=n` y `CONFIG_ESP_WIFI_RX_IRAM_OPT=n` pasan código del Wi-Fi a la flash.

## Flashear

Lo más simple es el kit, sin compilar (ver «Kit de flasheo»). Con lo recién compilado, desde el acceso directo «IDF_v5.4.4_Powershell» o la terminal de ESP-IDF en VS Code:

```powershell
idf.py -C firmware -B firmware\build-esp32cam -p COM5 flash monitor
```

- La ESP32-CAM no tiene USB: va en su base con USB-C (ESP32-CAM-MB), que Windows muestra como «USB Serial Port» (`COM5` en el ejemplo). La base la pone sola en modo de descarga y la reinicia con DTR y RTS.
- Con un adaptador USB-TTL en vez de la base: 5V y GND, U0R al TX y U0T al RX del adaptador, y GPIO0 a GND. Presiona RST, flashea, quita el puente de GPIO0 y presiona RST otra vez.
- `Ctrl+]` sale del monitor.

## Kit de flasheo

`kit\firmware\`, que Git ignora, lleva los binarios listos para flashear sin compilar:

| Carpeta | Placa | De dónde sale |
| --- | --- | --- |
| `esp32cam` | ESP32-CAM AI-Thinker, la de la demo (D-24) | Este firmware |
| `s3-octal` | Respaldo: ESP32-S3 con PSRAM octal (ESP32-S3-EYE, Freenove ESP32-S3 WROOM CAM, XIAO ESP32S3 Sense u otra con un chip o módulo R8) | El firmware de referencia del PR #7 (D-17) |
| `s3-quad` | Respaldo: ESP32-S3 con PSRAM quad (un chip o módulo R2) | El firmware de referencia del PR #7 |

- Cada carpeta lleva el bootloader, la tabla de particiones, el programa, `flasher_args.json` y `origen.txt`, con el commit y las direcciones de fábrica.
- Todos apuntan a la Pi, con la IP de `ACCESIA_IP_DE_LA_PI`. Los del S3 se compilan desde una copia del PR #7 con esa IP en lugar de `10.42.0.1`, sin cambiar el PR.
- El binario de la XIAO ESP32-C6 ya no va en el kit (D-24).

Armar el kit, desde la raíz y en PowerShell:

```powershell
.\firmware\scripts\armar-kit.ps1                                  # compila la ESP32-CAM y arma kit\firmware
git fetch origin a/esp-idf-deteccion
git worktree add ..\AccesIA-s3 origin/a/esp-idf-deteccion         # una copia del PR #7, una vez
.\firmware\scripts\armar-kit.ps1 -FuenteS3 ..\AccesIA-s3          # también los binarios octal y quad del S3
```

Flashear la ESP32-CAM en su base y abrir su consola:

```powershell
.\kit\firmware\flashear.ps1 -Placa esp32cam -Puerto COM5 -Monitor
```

- Antes de flashear, dice qué placa va a flashear y cómo ponerla en modo de descarga.
- Flashea cada archivo en su dirección, como `idf.py flash`, así que la configuración de la consola (NVS, de `0x9000` a `0xF000`) se conserva. `-Borrar` borra toda la flash antes. En el ESP32 el bootloader va en `0x1000`.
- `-Monitor` abre miniterm con DTR y RTS en 0, para que la base no deje la placa en reset. La base tapa el botón RST: Ctrl+T y Ctrl+R dos veces reinician la placa. `.\kit\firmware\flashear.ps1 -Monitor -Puerto COM5` abre solo la consola.
- `-Detectar` dice qué chip está conectado; `-Placa s3-octal` o `s3-quad` flashean el respaldo.
- Usa el esptool del PATH o el de ESP-IDF 5.4. Con `-WhatIf` muestra el comando sin flashear.

## Consola

Los comandos entran por UART0, que en la ESP32-CAM es el USB de la base o el adaptador. En la XIAO ESP32-C6 también entran por el USB-C (USB Serial/JTAG). Se guardan en NVS: no hace falta recompilar (RF-01 · C4).

| Comando | Ejemplo |
| --- | --- |
| `estado` | Muestra el Wi-Fi, el servidor, el código, MQTT, la puerta y, en la ESP32-CAM, la cámara, el modelo, la presencia, el último envío, `cara_min` y la memoria |
| `wifi <ssid> <clave>` | `wifi AccesIA clave123`; si el nombre tiene espacios, va entre comillas |
| `servidor <url>` | `servidor http://192.168.137.250:8000` |
| `codigo <codigo>` | `codigo entrada`; de 3 a 32 letras minúsculas, números o guiones, y no `servidor` |
| `token <token>` | El token que da la web al crear la cámara |
| `mqtt <url> <usuario> <clave>` | `mqtt mqtt://192.168.137.250:1883 camara clave123` |
| `puerta <pin> <segundos> [bajo\|alto]` | `puerta 33 3 bajo`, lo de fábrica en la ESP32-CAM. El nivel es el que enciende; `-1` si no hay LED ni relé; de 1 a 60 s |
| `cara_min <px>` | `cara_min 80`, igual que `CARA_MIN_PX` del servidor (solo la ESP32-CAM) |
| `sensor <dht22\|dht11>` | `sensor dht11` (solo el C6) |
| `antena <interna\|externa>` | `antena externa` (solo el C6) |
| `reiniciar` | Reinicia la placa |
| `ayuda` | Lista los comandos |

- Valores de fábrica (`arquitectura.md`): Wi-Fi «AccesIA»; servidor `http://192.168.137.250:8000` y MQTT `mqtt://192.168.137.250:1883`, los de la Pi (D-22), con el usuario `camara`; la puerta en el LED rojo (GPIO33, 3 s, enciende en bajo) y `cara_min` 80 px.
- `estado` no muestra las claves ni el token. Quedan en la placa sin cifrar.
- En la ESP32-CAM, `puerta` acepta GPIO 2, 4, 13, 14, 15 y 33. Rechaza los de la cámara, la flash, UART0 (1 y 3), la PSRAM (16 y 17), los que solo son entrada (34 a 39) y GPIO12, que decide el voltaje de la flash al arrancar.
- `codigo` borra antes el descubrimiento retenido de la placa, porque con el código nuevo la ACL ya no la deja.

## Qué hace la ESP32-CAM

| Pin | Uso |
| --- | --- |
| GPIO0, 5, 18, 19, 21, 22, 23, 25, 26, 27, 32, 34, 35, 36 y 39 | La cámara OV2640, con el perfil AI-Thinker de esp32-camera. GPIO0 es XCLK y, a GND al arrancar, el modo de descarga |
| GPIO33 | LED rojo, que enciende en bajo: la puerta y el estado de la placa |
| GPIO4 | LED blanco del flash; queda apagado |
| GPIO1 y GPIO3 | UART0: la consola y el flasheo |
| GPIO16 y GPIO17 | La PSRAM |

- Al arrancar se conecta al Wi-Fi (reintentos de 1, 2, 4, 8 y 10 s) y a MQTT con su código como client id. Después inicia la cámara, en QVGA (320 × 240) y RGB565, con dos cuadros en la PSRAM.
- **Detección (RF-01 · C1).** Una tarea, en el núcleo 1, toma cada cuadro y corre ESP-DL 1.1: MSR01 propone candidatas y MNP01 confirma cada una. Medido en la placa (P-05): MSR de 55 a 70 ms por cuadro y MNP de 102 ms por candidata. Con una cara, el cuadro completo, con el JPEG del recorte, toma de 230 a 440 ms.
- **Envío (RF-01 · C2 y C3).** Si la cara más grande mide al menos `cara_min` de alto, la recorta con la fórmula del contrato, la comprime en JPEG de calidad 80 (de 6,5 a 9,4 KB, medido) y la pasa a la tarea de envío, en el núcleo 0. Esa tarea hace el `POST` con el token, `X-AccesIA-Firmware` (`tinyml-esp32cam-<versión>`) y `X-AccesIA-Puntaje`. Mientras espera la respuesta, la detección sigue, pero no prepara otro recorte.
- **Respuestas** (tabla «Qué hace la cámara con la respuesta»): muestra el resultado y el mensaje por la consola; espera 3 s tras `permitido`, `denegado` o `desconocido` y 1 s tras lo demás; 30 s con 401 o 403; lo que diga `Retry-After` con 429; y 1, 2, 4, 8 y hasta 10 s sin respuesta en 5 s o con 5xx.
- **Presencia (`mqtt.md` 1.6).** `presente` pasa a `true` en el primer cuadro con una cara y vuelve a `false` **tras 5 s sin caras**: cubre los cuadros en que la cara gira o el modelo no la ve, para que no parpadee. El puntaje es el de la última cara. Se publica retenida, con QoS 1, cada vez que cambia y cada vez que se conecta al broker, con el descubrimiento de su `binary_sensor` de ocupación.
- **MQTT.** Se suscribe a `accesia/{codigo}/puerta/set`. Al conectarse publica `online`, el descubrimiento, la presencia, la puerta y su estado general (con `psram_kb`), que repite cada 60 s. El último deseo publica `offline`.
- **Puerta.** Con `ABRIR` enciende el LED rojo los segundos configurados y publica `abierta` y luego `cerrada`; `CERRAR` lo apaga antes. El resto del tiempo el LED parpadea despacio sin Wi-Fi, rápido sin broker y queda apagado con todo conectado.
- **Memoria.** ESP-DL 1.1 reserva sus búferes primero en la RAM interna y, en cada detección, toma la que haya libre (en la prueba de factibilidad, sin Wi-Fi, bajó a 57 KB). Por eso los búferes del Wi-Fi y de lwIP van a la PSRAM (`CONFIG_SPIRAM_TRY_ALLOCATE_WIFI_LWIP`), y el Wi-Fi arranca antes que la cámara. La memoria interna mínima sale en `estado` y cada 60 s por la consola.
- Ninguna imagen se guarda: el cuadro vuelve a la cámara y el JPEG del recorte se libera al enviarse (RNF-01).

La XIAO ESP32-C6 (D-21) hace lo de siempre: la puerta en su LED (GPIO15), el estado y, cada 30 s, la temperatura y la humedad de un DHT en GPIO2. Sus pines están en `arquitectura.md`.

## Prueba con la placa

Con la demo de D-22: el servidor, la base y el broker en la Pi, con sus complementos (`complementos/README.md`), y la Pi en el hotspot del portátil.

1. **Red.** El hotspot del portátil se llama `AccesIA` y va en 2,4 GHz: el ESP32 no usa 5 GHz. Windows solo lo enciende si el portátil tiene una conexión que compartir. La lista «Dispositivos conectados» muestra la IP de la placa y la de la Pi.
2. **La cámara en la web.** En la pantalla Cámaras, crea la cámara `entrada` (si no existe) y copia su token: se muestra una sola vez.
3. **La placa.** Flashéala y abre la consola (ver «Kit de flasheo»). Escribe:

```text
wifi AccesIA <clave del hotspot>
codigo entrada
token <el token de la cámara entrada>
mqtt mqtt://192.168.137.250:1883 camara <MQTT_CAMARA_CLAVE>
reiniciar
estado
```

- Si la Pi quedó en otra IP, también `servidor http://<IP>:8000` y esa IP en `mqtt`.
- El código es el client id de MQTT: el simulador no puede estar conectado a la vez con el mismo código.

### Qué comprobar

| Criterio | Cómo se ve |
| --- | --- |
| Conexión | El LED rojo parpadea despacio mientras busca el Wi-Fi, rápido mientras llega al broker, y se apaga. `estado` muestra el broker conectado; `accesia/entrada/disponible` queda en `online` |
| RF-01 · C1 | Frente a la cámara, a 0,5 o 1 m, la consola muestra `Presencia: {"presente": true, …}`. `estado` muestra cuánto tardó la última detección |
| RF-01 · C2 y C3 | La consola muestra `Servidor: <resultado> · <mensaje>` y la web registra el evento. Sin cara, o con una cara más baja que `cara_min`, no envía nada |
| Presencia (`mqtt.md` 1.6) | En Home Assistant, el dispositivo de la cámara tiene la entidad Presencia, aunque el servidor esté apagado. Pasa a «Detectado» con una cara y a «Despejado» unos 5 s después de que se va |
| Puerta | Un acceso `permitido` abre la puerta: el LED rojo se enciende 3 s y `accesia/entrada/puerta/estado` pasa a `abierta` y luego a `cerrada` |
| Memoria | Cada 60 s, `Memoria: interna libre … (mínimo …)`. El mínimo no debe acercarse a cero |
| RF-01 · C4 | Todo lo anterior se configuró por consola, sin recompilar |

### Si algo falla

| Qué pasa | Qué revisar |
| --- | --- |
| Se reinicia con «Brownout detector was triggered» | La alimentación: la ESP32-CAM pide 5 V con buena corriente al encender el Wi-Fi y la cámara. Usa otro cable o puerto USB |
| «No arrancó la cámara» | El cable plano de la cámara, bien metido y con el seguro cerrado. `estado` muestra el error |
| La placa no ve la red | La banda de 2,4 GHz, el nombre y la clave del hotspot |
| El LED sigue parpadeando rápido | Que el broker de la Pi corra, la clave de `camara` y que no haya otro cliente con el mismo código |
| `El servidor no acepta esta cámara (401…)` | El código y el token, con `codigo` y `token`. La cámara reintenta cada 30 s |
| `Sin respuesta del servidor` | Que el servidor de la Pi corra y la IP de `servidor` |
| La entidad Presencia no aparece | Que la ACL de la Pi sea la de `mqtt.md` 1.6, con las líneas de la presencia |

## Pruebas de la lógica pura

```powershell
.\firmware\scripts\probar-logica.ps1
```

- Corren en un contenedor `ubuntu:24.04` de Docker Desktop, que se borra al terminar. El contenedor instala g++, CMake y Ninja y compila `firmware/pruebas/` con doctest 2.5.3 y nlohmann/json 3.12.0, que se descargan comprobando su huella SHA-256.
- Prueban los mismos archivos que compila ESP-IDF, los de `components/accesia_logica` y `components/accesia_recorte`:
  - la presencia y su descubrimiento, como en el contrato, y los 5 s sin caras (`contrato MQTT · presencia`, `contrato MQTT · descubrimiento de la placa · presencia` y `D-24 · presencia`);
  - el envío: la URL, el puntaje y la espera tras cada respuesta (`contrato cámara · <respuesta>`);
  - el recorte y la espera entre recortes (`contrato recorte · <caso>`, `RF-01 · C2`, `RF-01 · C3` y `contrato cámara · espera 3 s`);
  - los pines de la ESP32-CAM y los que acepta `puerta` (`D-24 · pines`);
  - el estado general, con y sin PSRAM (`contrato MQTT · estado`);
  - del C6: el ambiente, la antena, los pines, la puerta y el LED (`contrato MQTT · ambiente`, `RF-14 · C2` a `C6`).
- Corren con el detector de comportamiento indefinido de GCC, y con `-Werror`.
- En Linux, sin Docker: `bash firmware/scripts/probar-logica.sh`.
- GitHub Actions (`.github/workflows/firmware.yml`) compila los dos targets, `esp32` y `esp32c6`, con la imagen `espressif/idf:v5.4.4`, revisa que sus `dependencies.lock` estén al día y corre estas pruebas en cada PR.

## Dependencias

Las versiones están fijas en `main/idf_component.yml`, con reglas por target. `dependencies.lock.esp32` y `dependencies.lock.esp32c6`, en Git, fijan también las dependencias de esas dependencias.

| Componente | Versión | Target | Por qué esa |
| --- | --- | --- | --- |
| `espressif/esp32-camera` | 2.1.9 | `esp32` | La misma del firmware del S3 (PR #7). Trae el perfil AI-Thinker y `fmt2jpg` para el JPEG del recorte |
| `espressif/esp-dl` | 1.1.0 | `esp32` | `HumanFaceDetectMSR01` + `MNP01`, ya compilados para el ESP32 clásico. No declara versión de ESP-IDF, y compila y corre con la 5.4.4 (P-05). La 2.0.0 exige ESP-IDF 5.0, y `human_face_detect`, de ESP-DL 3, solo trae modelos del S3 y del P4 |
| `esp-idf-lib/dht` | 1.2.0 | `esp32c6` | Lee el DHT22 y el DHT11 y declara soporte para el `esp32c6` |
| `esp-idf-lib/esp_idf_lib_helpers` | 1.4.0 | `esp32c6` | `dht` la pide sin versión; se fija aquí |

ESP-DL 1.1 viene compilada, sin código fuente, y reserva sus búferes primero en la RAM interna (ver «Memoria»). La placa del equipo es una ESP32-D0WD-V3, revisión v3.1, así que no le afecta el error de caché de la PSRAM de la revisión 1.

## Estructura

```text
firmware/
├── CMakeLists.txt              proyecto ESP-IDF (versión 0.3.0); target esp32 por defecto y un lockfile por target
├── sdkconfig.defaults          común: rendimiento, flash de 4 MB, particiones y consola en UART0
├── sdkconfig.defaults.esp32    la ESP32-CAM: 240 MHz, PSRAM y los búferes del Wi-Fi en la PSRAM
├── sdkconfig.defaults.esp32c6  el C6: 160 MHz y la consola también por el USB
├── particiones.csv             nvs, phy_init y factory de 3 MB
├── dependencies.lock.esp32     versiones exactas de las dependencias de la ESP32-CAM
├── dependencies.lock.esp32c6   versiones exactas de las dependencias del C6
├── main/                       arranque; idf_component.yml con las versiones
├── components/
│   ├── accesia_config/         configuración en NVS; valores_de_fabrica.hpp, con la IP de la Pi
│   ├── accesia_consola/        consola por UART0 y, en el C6, por el USB nativo
│   ├── accesia_red/            Wi-Fi, IP y señal
│   ├── accesia_mqtt/           temas, descubrimiento, presencia, último deseo y estado general
│   ├── accesia_puerta/         la puerta en el LED o en un relé
│   ├── accesia_camara/         la OV2640 y el JPEG del recorte (solo esp32)
│   ├── accesia_deteccion/      caras con ESP-DL 1.1 (solo esp32)
│   ├── accesia_envio/          el POST del recorte y su respuesta (solo esp32)
│   ├── accesia_esp32cam/       el ciclo de visión y envío, el LED rojo y cara_min (solo esp32)
│   ├── accesia_ambiente/       sensor DHT (solo C6)
│   ├── accesia_placa_c6/       antena, LED y pines de la XIAO ESP32-C6 (solo C6)
│   ├── accesia_logica/         lógica pura: mensajes, presencia, puerta, ambiente, LED y pines
│   ├── accesia_recorte/        lógica pura del recorte, la espera y el envío
│   └── accesia_vision/         interfaces de la fuente de cuadros y del detector
├── pruebas/                    pruebas de la lógica pura (CMake y doctest)
└── scripts/                    compilar.ps1, probar-logica.ps1 y .sh, armar-kit.ps1 y flashear.ps1
```

## Por verificar con la placa

- La memoria interna mínima con Wi-Fi, MQTT y HTTP andando (sin ellos, la prueba de factibilidad bajó a 57 KB).
- El envío al servidor de la Pi y las respuestas, con la cámara creada en la web.
- La presencia en Home Assistant, con la ACL de `mqtt.md` 1.6.
- La puerta en el LED rojo con `ABRIR`, y que GPIO33 encienda en bajo.
- Que la cámara entregue cuadros estables con XCLK a 20 MHz mientras el Wi-Fi transmite.
