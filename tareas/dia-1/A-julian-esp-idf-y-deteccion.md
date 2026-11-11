<!--
Nombre: A-julian-esp-idf-y-deteccion.md
Descripción: Tarea del Día 1 del frente A: proyecto ESP-IDF de la cámara con detección TinyML, perfiles de placa y consola.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 1 · Frente A · ESP-IDF y detección TinyML

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/esp-idf-deteccion`
- Lee primero: `CLAUDE.md`; `specs/arquitectura.md` (Firmware de la cámara); `specs/requisitos.md` (RF-01); `specs/contratos/api-dispositivo.md`; `specs/contratos/mqtt.md` (la parte de la cámara); `specs/decisiones.md` (D-02, D-17 y D-18).

## Objetivo

Dejar el proyecto ESP-IDF de la cámara compilando con la detección de caras de ESP-DL para ESP32-S3, con perfiles de placa y consola serial. Todavía no hay placa: lo que se comprueba es que compile para todos los perfiles y que la lógica pura tenga pruebas.

## Antes de empezar

- Instalar ESP-IDF v5.4 con la extensión ESP-IDF de VS Code (Espressif) en Windows. Es la versión con la que el ejemplo de detección de ESP-DL declara soporte para ESP32-S3.
- Comprobar la instalación compilando el ejemplo `human_face_detect` del componente `espressif/esp-dl` (versión vigente en el ESP Component Registry) para `esp32s3`.

## Hacer

1. Proyecto `firmware/` (ESP-IDF, C++):
   - Dependencias en `main/idf_component.yml`, con versiones fijas: `espressif/esp32-camera` y `espressif/human_face_detect` (modelo MSR_S8_V1 + MNP_S8_V1).
   - Componentes propios:

     | Componente | Qué hace |
     | --- | --- |
     | `accesia_config` | Lee y guarda la configuración en NVS |
     | `accesia_consola` | Consola serial con los comandos de `arquitectura.md` |
     | `accesia_perfiles` | Pines y ajustes de cada placa |
     | `accesia_camara` | Inicia la cámara según el perfil y captura en QVGA |
     | `accesia_deteccion` | Corre `HumanFaceDetect` sobre el cuadro |
     | `accesia_recorte` | Elige la cara más grande y calcula el recorte con 25 % de margen dentro del cuadro (lógica pura, sin hardware) |

   - Los cinco perfiles de `arquitectura.md`: un `sdkconfig.defaults` común y uno por perfil (PSRAM octal o quad, CPU a 240 MHz, optimización por rendimiento).
   - Pines tomados de la documentación oficial de cada placa, con la fuente citada en el código y marcados «por verificar con la placa».
   - Tabla de particiones que cabe en 4 MB.
   - `main`: arranca, lee la configuración, inicia la cámara y en un bucle detecta y muestra por el monitor serial cada cara (caja y puntaje) y el recorte que enviaría (tamaño en píxeles y en bytes). El envío por HTTP y la puerta por MQTT son del Día 3.
2. `firmware/scripts/compilar-perfiles.ps1`: compila todos los perfiles, cada uno en su carpeta `firmware/build-<perfil>/` (Git las ignora).
3. Pruebas de la lógica pura que corren en el PC, sin placa: recorte con margen y ajuste a los bordes, descarte de caras menores que `cara_min`, y límite de un envío por segundo. Usa lo más simple (el target `linux` de ESP-IDF o CMake con una librería de pruebas) y explica la elección.
4. `firmware/README.md`: instalación, compilar, flashear cuando haya placa y comandos de la consola.

## No hacer

- No inventes pines: si una placa no tiene fuente oficial clara, deja el perfil marcado y avisa.
- No envíes imágenes completas ni guardes fotos en la placa.
- No cambies los contratos: si algo no encaja, propón el cambio.

## Criterios de aceptación

- C1 (RF-01 · C5) `idf.py build` pasa para los cinco perfiles, y el script los compila todos.
- C2 (RF-01 · C1) La detección usa `espressif/human_face_detect` (MSR + MNP, int8).
- C3 (RF-01 · C4) La consola tiene los comandos de `arquitectura.md` y los guarda en NVS.
- C4 (RF-01 · C2 y C3) Las pruebas del recorte pasan: margen de 25 %, ajuste a los bordes y nada si la cara mide menos de `cara_min`.
- C5 La bitácora y `firmware/README.md` están al día.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado, y qué queda por probar cuando llegue la placa.
- PR a `main` con los criterios cumplidos.
