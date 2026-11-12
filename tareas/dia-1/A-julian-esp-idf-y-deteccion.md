<!--
Nombre: A-julian-esp-idf-y-deteccion.md
Descripción: Tarea del Día 1 del frente A: proyecto ESP-IDF de la cámara con detección TinyML, perfiles de placa y consola.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Día 1 · Frente A · ESP-IDF y detección TinyML

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/esp-idf-deteccion`
- Lee primero: `CLAUDE.md`; `specs/arquitectura.md` (Firmware de la cámara); `specs/requisitos.md` (RF-01); `specs/contratos/api-dispositivo.md` (con la fórmula del recorte) y `specs/contratos/casos-recorte.json`; `specs/contratos/mqtt.md` (la parte de la cámara); `specs/decisiones.md` (D-02, D-17 y D-18).

## Objetivo

Dejar el proyecto ESP-IDF de la cámara compilando con la detección de caras de ESP-DL para ESP32-S3, en sus dos binarios (`octal` y `quad`), con perfiles de placa y consola serial. Todavía no hay placa: lo que se comprueba es que compilen los dos binarios y que la lógica pura tenga pruebas.

## Antes de empezar

- Instalar ESP-IDF v5.4 con la extensión ESP-IDF de VS Code (Espressif) en Windows.
- Buscar en el ESP Component Registry la última versión de `espressif/human_face_detect` (y de `espressif/esp-dl`) que declare soporte para ESP-IDF 5.4, y comprobar la instalación compilando su ejemplo para `esp32s3`. Si ninguna versión sirve con 5.4, subir ESP-IDF a la versión que pidan. La versión elegida queda fija en `idf_component.yml` y anotada en la bitácora.
- Tener Docker Desktop abierto: las pruebas de la lógica pura corren en un contenedor `ubuntu:24.04` (paso 3). Cambio del 2026-11-12: antes decía instalar WSL con Ubuntu; el equipo decidió usar el contenedor y no instalarlo.

## Hacer

1. Proyecto `firmware/` (ESP-IDF, C++):
   - Dependencias en `main/idf_component.yml`, con versiones fijas: `espressif/esp32-camera` y `espressif/human_face_detect` (modelo MSR_S8_V1 + MNP_S8_V1). El `dependencies.lock` se sube al repositorio para fijar también las dependencias de ESP-DL.
   - Componentes propios:

     | Componente | Qué hace |
     | --- | --- |
     | `accesia_config` | Lee y guarda la configuración en NVS |
     | `accesia_consola` | Consola serial con los comandos de `arquitectura.md` |
     | `accesia_perfiles` | Pines y ajustes de cada placa |
     | `accesia_camara` | Inicia la cámara según el perfil y captura en QVGA |
     | `accesia_deteccion` | Corre `HumanFaceDetect` sobre el cuadro |
     | `accesia_recorte` | Elige la cara de mayor área y calcula el recorte con la fórmula de `api-dispositivo.md` (lógica pura, sin hardware) |

   - Los dos binarios de `arquitectura.md` (D-17): un `sdkconfig.defaults` común (CPU a 240 MHz, optimización por rendimiento) y uno por binario, `sdkconfig.defaults.octal` y `sdkconfig.defaults.quad`, con su tipo de PSRAM. Los cinco perfiles viven en `accesia_perfiles`; el comando `perfil` elige entre los del binario cargado.
   - Pines tomados de la documentación oficial de cada placa, con la fuente citada en el código y marcados «por verificar con la placa».
   - Tabla de particiones que cabe en 4 MB.
   - `main`: arranca, lee la configuración, inicia la cámara y en un bucle detecta y muestra por el monitor serial cada cara (caja y puntaje) y el recorte que enviaría (tamaño en píxeles y en bytes). El envío por HTTP y la puerta por MQTT son del Día 3.
2. `firmware/scripts/compilar-binarios.ps1`: compila los dos binarios, en `firmware/build-octal/` y `firmware/build-quad/` (Git ignora `firmware/build-*/`). El `.ps1` va en UTF-8 con BOM, como pide `.editorconfig`: sin BOM, Windows PowerShell 5.1 lee mal las tildes.
3. Pruebas de la lógica pura, sin placa, con CMake y doctest. Corren en un contenedor `ubuntu:24.04` de Docker Desktop (`firmware/scripts/probar-logica.ps1`), porque el target `linux` de ESP-IDF no funciona en Windows; desde el Día 4, en GitHub Actions. Cubren:
   - Los casos de `specs/contratos/casos-recorte.json`, leídos del archivo (marca `contrato recorte · <caso>`): la cara de mayor área, el margen y el ajuste a los bordes.
   - El descarte de caras menores que `cara_min`.
   - La espera entre recortes: al menos 1 s desde que llega la respuesta, y 3 s tras `permitido`, `denegado` o `desconocido`.
4. `firmware/README.md`: instalación, compilar, flashear cuando haya placa, elegir el perfil, comandos de la consola y cómo correr las pruebas en el contenedor.

## No hacer

- No inventes pines: si una placa no tiene fuente oficial clara, deja el perfil marcado y avisa.
- No envíes imágenes completas ni guardes fotos en la placa.
- No cambies los contratos: si algo no encaja, propón el cambio.
- No crees todavía `.github/workflows/firmware.yml`: el firmware se suma a GitHub Actions el Día 4.

## Criterios de aceptación

- C1 (RF-01 · C5) `idf.py build` pasa para los dos binarios, `octal` y `quad`, y el script compila los dos.
- C2 (RF-01 · C1) La detección usa `espressif/human_face_detect` (MSR + MNP, int8).
- C3 (RF-01 · C4) La consola tiene los comandos de `arquitectura.md` y los guarda en NVS.
- C4 (RF-01 · C2, C3 y C6) Las pruebas pasan en el contenedor `ubuntu:24.04` (antes decía WSL; cambio del 2026-11-12): los casos de `casos-recorte.json`, nada si la cara mide menos de `cara_min` y la espera entre recortes.
- C5 La bitácora y `firmware/README.md` están al día.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado, y qué queda por probar cuando llegue la placa.
- PR a `main` con los criterios cumplidos.
