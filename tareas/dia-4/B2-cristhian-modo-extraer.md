<!--
Nombre: B2-cristhian-modo-extraer.md
Descripción: Tarea B2 del Día 4 del frente B: el modo extraer (RF-10 · C4). Para una cámara de tipo respaldo, el servidor pide su imagen cada segundo, recorta la cara más grande y la procesa como un recorte de la cámara.
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.1
-->

# Día 4 · Frente B · B2 · El modo extraer

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/modo-extraer`
- Depende de: nada del día. B1 ya está en `main` (PR #19), así que B2 parte de ahí.
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - `specs/contratos/api-dispositivo.md` completo, en especial «Modo extraer (cámara de respaldo)» y las esperas de la cámara;
  - de `specs/requisitos.md`, RF-10 · C4 y RF-05 · C2;
  - de `specs/arquitectura.md`, Firmware: «Cuando llegue el módulo de cámara», donde está el ESP32-CAM;
  - de `specs/decisiones.md`, D-21 y D-22 (con D-22, el servidor corre en la Pi);
  - de `servidor/README.md`, Reconocimiento e inscripción, MQTT y Registro.

## Objetivo

Una cámara de tipo `respaldo` funciona sin firmware de AccesIA (RF-10 · C4):

- el servidor pide `GET {url_captura}` cada segundo, con 3 s de espera;
- detecta con YuNet en la imagen completa y recorta la cara más grande con la fórmula del contrato (`recortar_cara_mas_grande`, de B2 del Día 2);
- procesa el recorte como uno que llega por `enviarRostro`.

Sirve para un ESP32-CAM, si ese es el módulo de P-03, y para cualquier cámara que entregue un JPEG por HTTP.

## Antes de empezar

- Propón en el plan:
  - **Dónde corre:**
    - una tarea del arranque, como la del resumen de cada 5 minutos;
    - si pide las cámaras una por una o en paralelo;
    - cómo se entera, sin reiniciar, de una cámara nueva, desactivada o con otra URL.
  - **El ritmo:** «cada segundo» del contrato. Propón si también respeta las esperas de la cámara (3 s después de `permitido`, `denegado` o `desconocido`), para no repetir la puerta.
  - **Los errores:**
    - el tiempo de espera, una respuesta 4xx o 5xx y algo que no es JPEG;
    - una imagen demasiado grande: el tope de 100 KB del contrato es para recortes, así que propón el de un cuadro completo y por qué;
    - cómo se anota todo esto sin llenar el registro con una línea por segundo.
  - **Una imagen sin cara:** `descartado` sin evento (RF-05 · C2), sin una línea por segundo en el registro.
  - **El último contacto y `en_linea`:** se actualizan con cada captura buena. Esa cámara no tiene MQTT, así que solo cuenta el contacto.
  - **La inscripción:** una cámara de respaldo también inscribe (R7 y R9), por el mismo camino.
  - **MQTT:** sus eventos, alertas y resumen se publican igual que los de `enviarRostro`, después de confirmar la transacción y solo con conexión. Aquí no hay petición: la publicación va después del bloque de la transacción.
  - **La URL:** la escribe un administrador. Propón si se siguen redirecciones y qué esquemas se aceptan.
- Si algo de esto no está en el contrato y hace falta escribirlo, se propone el cambio de `api-dispositivo.md` en el PR, como dice `specs/contratos/README.md`.

## Hacer

1. El bucle del modo extraer, con su arranque y su parada en el ciclo de vida de la app.
2. El recorte y el procesamiento, por el mismo código de `enviarRostro`, sin duplicar reglas.
3. Los errores y el registro que se acuerden.
4. Pruebas, cada una con su marca (`RF-10 · C4` y `contrato cámara · modo extraer`):
   - Con una cámara HTTP falsa, sin red de verdad, con la visión armada y el reloj de las pruebas.
   - Lo que deben cubrir:
     - `permitido`, `desconocido` e inscripción;
     - sin cara, sin evento;
     - el tiempo de espera, un 500 y algo que no es JPEG, sin tumbar el bucle;
     - una cámara desactivada o borrada deja de pedirse;
     - el último contacto;
     - los eventos publicados en MQTT, con el broker de prueba de B2 del Día 3.
5. Una prueba a mano con una cámara HTTP de verdad, si hay: un ESP32-CAM, un celular con una aplicación que sirva un JPEG, o un servidor local que sirva una foto de `datos/prueba/`. Se crea con `crear-camara --tipo respaldo --url-captura …`.
6. `servidor/README.md` (cómo se usa y qué se decidió) y la bitácora.

## No hacer

- No guardes cuadros ni recortes: solo viven en memoria (RNF-01 · C1).
- No cambies `api-dispositivo.md` ni `openapi.yaml` sin proponerlo.
- No toques `firmware/`, `simulador/` ni `web/`.

## Criterios de aceptación

- C1 (RF-10 · C4) Una cámara `respaldo` activa reconoce e inscribe como cualquier otra, con sus eventos y su publicación en MQTT.
- C2 Los errores de una cámara no tumban el servidor ni frenan a las demás, y desactivarla detiene las capturas.
- C3 (RNF-01 · C1) Ningún cuadro se escribe en disco ni en el registro.
- C4 (RNF-06 · C3) `servidor.yml` en verde, con las marcas nuevas; `servidor/README.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué hiciste y qué pruebas corriste, con su resultado por marca;
  - el ritmo, el tope de tamaño y lo que decidiste sobre los errores;
  - si se probó con una cámara de verdad.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
