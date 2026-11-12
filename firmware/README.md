<!--
Nombre: README.md
Descripción: Firmware de la cámara ESP32-S3 de AccesIA (frente A): instalación, compilar, flashear, perfiles, consola y pruebas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Firmware de la cámara · frente A

Firmware del ESP32-S3 en ESP-IDF 5.4 (C++): detecta la cara con TinyML (ESP-DL), envía el recorte al servidor por HTTP y abre la puerta cuando Home Assistant lo pide por MQTT.

- Specs: `specs/arquitectura.md` (Firmware de la cámara), `specs/requisitos.md` (RF-01) y los contratos `api-dispositivo.md` y `mqtt.md`.
- Lo crea la tarea `tareas/dia-1/A-julian-esp-idf-y-deteccion.md`. Hay dos binarios, `octal` y `quad`, y el perfil de la placa se elige por consola (D-17). El envío y la puerta son del Día 3; los perfiles probados, el diagnóstico y el respaldo, del Día 4.
- Día 1: compilan los dos binarios. La placa detecta caras y muestra por el monitor serial cada cara y el recorte que enviaría, pero todavía no envía nada.

> En clase entregaron un Seeed Studio XIAO ESP32-C6 (4 MB de flash, sin PSRAM ni interfaz de cámara), no el ESP32-S3 del enunciado. Este firmware queda como referencia, en un PR borrador, por si se vuelve al S3. El del C6 sigue en la rama `a/firmware-c6`.

## Instalar ESP-IDF 5.4.4 (una vez)

Se instala con EIM (ESP-IDF Installation Manager), el instalador oficial de Espressif. Es el mismo que usa la extensión ESP-IDF de VS Code, así que la extensión encuentra la instalación sin configurar nada.

- Con VS Code: instala la extensión «ESP-IDF» de Espressif, corre `ESP-IDF: Open ESP-IDF Installation Manager` y elige v5.4.4 y `esp32s3`.
- Por línea de comandos, como se instaló el Día 1, con el ejecutable `eim-cli-windows-x64.exe` de [github.com/espressif/idf-im-ui/releases](https://github.com/espressif/idf-im-ui/releases) o con `winget install Espressif.EIM-CLI`:

```powershell
eim install -i v5.4.4 -t esp32s3 -p C:\esp -n true --do-not-track true
```

Queda así:

- ESP-IDF en `C:\esp\v5.4.4\esp-idf` y sus herramientas en `C:\Espressif\tools`. Esas rutas no pueden tener espacios.
- Un acceso directo «IDF_v5.4.4_Powershell» en el escritorio, que abre PowerShell con ESP-IDF activado.
- `C:\Espressif\tools\eim_idf.json`, donde la extensión de VS Code y `compilar-binarios.ps1` encuentran la instalación.

ESP-IDF se usa desde PowerShell, no desde Git Bash: `idf.py` no funciona en MSYS. La ruta del repositorio sí puede tener espacios («Inteligencia artificial»): con ESP-IDF 5.4.4 compila bien.

## Compilar

Desde la raíz del repositorio, en PowerShell:

```powershell
.\firmware\scripts\compilar-binarios.ps1                 # los dos binarios, en firmware\build-octal y firmware\build-quad
.\firmware\scripts\compilar-binarios.ps1 -Binario quad   # solo uno
```

- Si `idf.py` no está a mano, el script activa ESP-IDF 5.4 con lo que dejó EIM en `eim_idf.json`.
- Cada binario usa `sdkconfig.defaults` más el suyo (`sdkconfig.defaults.octal` o `.quad`) y guarda su `sdkconfig` dentro de su carpeta. Git ignora `build-*/`, `sdkconfig` y `managed_components/`.
- La primera vez baja las dependencias del ESP Component Registry y tarda unos minutos; después, ccache acelera.
- Un `idf.py build` sin el script, como el botón de compilar de VS Code, compila el binario octal en `firmware/build/`.

| Binario | PSRAM | Perfiles | Tamaño el Día 1 |
| --- | --- | --- | --- |
| `octal` | octal | `esp32s3_eye`, `freenove_s3_cam`, `xiao_s3_sense`, `generico_octal` | 1,56 MB, el 50 % de la partición |
| `quad` | quad | `generico_quad` | 1,55 MB, el 49 % de la partición |

La partición `factory` mide 3 MB, y la tabla completa (`particiones.csv`) cabe en 4 MB de flash. Por eso el mismo binario sirve en placas de 4, 8 y 16 MB.

## Flashear (cuando llegue la placa)

Desde el acceso directo «IDF_v5.4.4_Powershell» o la terminal de ESP-IDF en VS Code, con la placa conectada por USB. El puerto (`COM5` en el ejemplo) aparece en el Administrador de dispositivos.

```powershell
idf.py -C firmware -B firmware\build-octal -p COM5 flash monitor
```

`Ctrl+]` sale del monitor. Si el binario no coincide con la PSRAM de la placa, no arranca. El binario `diagnostico` del Día 4 dice cuál usar.

## Elegir el perfil

La primera vez la placa arranca sin perfil y no inicia la cámara: así no mueve pines en una placa desconocida. Por el monitor serial:

```text
perfil                 lista los perfiles de este binario
perfil esp32s3_eye     lo guarda
reiniciar
```

En los perfiles genéricos se define cada pin con `pin <nombre> <número>`. Son obligatorios `xclk`, `siod`, `sioc`, `d0` a `d7`, `vsync`, `href` y `pclk`; `pwdn` y `reset` pueden quedar en `-1`. La consola rechaza estos GPIO:

- los de la flash y la PSRAM, del 26 al 32, y del 33 al 37 en el binario octal;
- los del USB nativo, 19 y 20;
- los de UART0, 43 y 44.

De dónde salen los pines de cada placa. Todos están por verificar con la placa:

| Perfil | Fuente |
| --- | --- |
| `esp32s3_eye` | BSP oficial de Espressif: `esp-bsp`, `bsp/esp32_s3_eye/include/bsp/esp32_s3_eye.h`. La imagen va volteada (`BSP_CAMERA_VFLIP`). |
| `freenove_s3_cam` | Repositorio oficial de Freenove, `Freenove_ESP32_S3_WROOM_Board`, `Sketch_07.1_CameraWebServer`: usa el modelo `CAMERA_MODEL_ESP32S3_EYE`, con los mismos pines del EYE. Con el sensor OV2640, el sketch voltea y refleja la imagen. |
| `xiao_s3_sense` | `camera_pins.h` del ejemplo CameraWebServer de `espressif/arduino-esp32` (`CAMERA_MODEL_XIAO_ESP32S3`), que coincide con la tabla de la wiki de Seeed. |

## Consola

Los comandos entran por UART0 y por el USB nativo (USB Serial/JTAG), el que tenga la placa. Se guardan en NVS y no hace falta recompilar.

| Comando | Ejemplo |
| --- | --- |
| `estado` | Muestra perfil, Wi-Fi, IP, servidor, MQTT y PSRAM |
| `wifi <ssid> <clave>` | `wifi AccesIA clave123`; si el nombre tiene espacios, va entre comillas |
| `servidor <url>` | `servidor http://10.42.0.1:8000` |
| `codigo <codigo>` | `codigo entrada`; de 3 a 32 letras minúsculas, números o guiones, y no `servidor` |
| `token <token>` | El token que da la web al crear la cámara |
| `mqtt <url> <usuario> <clave>` | `mqtt mqtt://10.42.0.1:1883 camara clave123` |
| `perfil [nombre]` | `perfil generico_octal`; sin nombre, lista los perfiles de este binario |
| `pin <nombre> <número>` | `pin xclk 15` (solo perfiles genéricos) |
| `puerta <pin> <segundos>` | `puerta 2 3`; `-1` si no hay LED ni relé; de 1 a 60 s |
| `cara_min <px>` | `cara_min 80` (igual que `CARA_MIN_PX` del servidor) |
| `reiniciar` | Reinicia la placa |
| `ayuda` | Lista los comandos |

- Valores por defecto (`arquitectura.md`):
  - Wi-Fi «AccesIA».
  - Servidor `http://10.42.0.1:8000`.
  - MQTT `mqtt://10.42.0.1:1883` con el usuario `camara`.
  - `cara_min` de 80 px.
  - La puerta, sin pin y 3 s.
- `estado` no muestra las claves ni el token. Quedan en la placa sin cifrar.
- Cómo funciona: la consola de ESP-IDF tiene UART0 como principal y el USB nativo como secundario, y el secundario solo envía texto. Por eso dos tareas propias leen los comandos de los dos puertos y los pasan a `esp_console_run`.

## Qué hace en el Día 1

Una vez por segundo:

1. Captura un cuadro en QVGA (320 × 240, RGB565).
2. Detecta las caras con `HumanFaceDetect` y el modelo `human_face_detect_msrmnp_s8_v1`, que es MSR + MNP en int8, y muestra la caja y el puntaje de cada una.
3. Elige la de mayor área. Si mide menos de `cara_min` de alto, no se enviaría nada.
4. Calcula el recorte con la fórmula de `api-dispositivo.md`, lo comprime en JPEG de calidad 80 y muestra su tamaño en píxeles y en bytes.

El JPEG se libera en la misma vuelta: no se guarda ninguna imagen.

## Pruebas de la lógica pura

```powershell
.\firmware\scripts\probar-logica.ps1
```

- Corren en un contenedor `ubuntu:24.04` de Docker Desktop, que se borra al terminar. El contenedor instala g++, CMake y Ninja y compila `firmware/pruebas/` con doctest 2.5.3 y nlohmann/json 3.12.0, que se descargan comprobando su huella SHA-256.
- Prueban los mismos archivos de `components/accesia_recorte` que compila ESP-IDF:
  - los casos de `specs/contratos/casos-recorte.json` (marca `contrato recorte · <caso>`);
  - `cara_min` (`RF-01 · C3`);
  - la espera entre recortes (`RF-01 · C2` y `contrato cámara · espera 3 s`).
- Corren con el detector de comportamiento indefinido de GCC, y con `-Werror`.
- En Linux, sin Docker: `bash firmware/scripts/probar-logica.sh`. Desde el Día 4 las corre GitHub Actions.

## Dependencias

Las versiones están fijas en `main/idf_component.yml`. `dependencies.lock`, en Git, fija también las dependencias de esas dependencias.

| Componente | Versión | Por qué esa |
| --- | --- | --- |
| `espressif/esp32-camera` | 2.1.9 | Descarta los cuadros que la PSRAM del S3 no recibió completos |
| `espressif/human_face_detect` | 0.5.2 | La última; trae el modelo MSR + MNP en int8 |
| `espressif/esp-dl` | 3.3.14 | La publicada con notas que pide `human_face_detect` 0.5.2 (`~3.3.14`); la 3.3.15 cambió los kernels del S3 |

## Estructura

```text
firmware/
├── CMakeLists.txt            proyecto ESP-IDF (versión 0.1.0)
├── sdkconfig.defaults        común: 240 MHz, rendimiento, flash de 4 MB, consola y modelo
├── sdkconfig.defaults.octal  PSRAM octal
├── sdkconfig.defaults.quad   PSRAM quad
├── particiones.csv           nvs, phy_init y factory de 3 MB
├── dependencies.lock         versiones exactas de todas las dependencias
├── main/                     arranque y bucle de detección; idf_component.yml con las versiones
├── components/
│   ├── accesia_config/       configuración en NVS
│   ├── accesia_consola/      consola por UART0 y por el USB nativo
│   ├── accesia_perfiles/     pines y ajustes de cada placa
│   ├── accesia_camara/       cámara en QVGA y JPEG del recorte
│   ├── accesia_deteccion/    HumanFaceDetect de ESP-DL
│   └── accesia_recorte/      lógica pura: cara mayor, recorte, cara_min y espera
├── pruebas/                  pruebas de la lógica pura (CMake y doctest)
└── scripts/                  compilar-binarios.ps1, probar-logica.ps1 y probar-logica.sh
```

## Por verificar con la placa

- Los pines y la orientación de cada perfil.
- El tipo de PSRAM.
- Que los comandos entren por los dos puertos.
- El sensor de la cámara y cuánto tarda la detección; el monitor serial muestra el tiempo de cada una.
