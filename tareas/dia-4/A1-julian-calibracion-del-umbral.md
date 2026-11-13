<!--
Nombre: A1-julian-calibracion-del-umbral.md
Descripción: Tarea A1 del Día 4 del frente A: calibrar UMBRAL_SIMILITUD y NITIDEZ_MIN con los tres integrantes y un dataset público de impostores, con recortes como los de la cámara (RNF-07), sin ensuciar la base del Compose.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 4 · Frente A · A1 · Calibración del umbral

- Responsable: Julián Andrés Silva Morales (frente A)
- Rama: `a/calibracion`
- Depende de:
  - las fotos de los tres integrantes en `datos/prueba/`, con su permiso (Ley 1581);
  - un dataset público de caras como impostores, con su licencia;
  - nada de B ni de C para empezar.
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/requisitos.md`, RNF-07 y RNF-01;
  - de `specs/reglas.md`, R1 y R7;
  - de `specs/decisiones.md`, D-14;
  - de `specs/arquitectura.md`, Piezas (los modelos) y Simulador;
  - `simulador/README.md`, en especial el modo carpeta y el modo «como la cámara»;
  - de `servidor/README.md`, Modelos de cara y Registro (la `calidad` de cada muestra).

## Objetivo

`UMBRAL_SIMILITUD` y `NITIDEZ_MIN` salen de datos medidos, con recortes como los de la cámara (RNF-07):

- ningún impostor se acepta;
- cada integrante tiene a lo sumo 2 rechazos de 20 intentos.

Los valores quedan anotados y son los que lleva el kit.

## Antes de empezar

- Propón en el plan cómo se mide sin ensuciar la base del Compose de la carpeta principal:
  - Por la API, cada `permitido` crea una llegada (R5) y tres desconocidos seguidos disparan la alerta de R6 en Home Assistant.
  - Una opción es un comando que use la misma visión del servidor (YuNet + SFace) y el recorte «como la cámara» del simulador, en memoria y sin base. Otra es una base aparte.
- Propón también:
  - qué dataset público de impostores, con su licencia, cuántas caras y cómo se baja (a `datos/`, nunca al repositorio);
  - cómo se separan las muestras de inscripción (5 por persona, R7) de los intentos (20 por persona);
  - qué reporta la medición: las similitudes de genuinos y de impostores, los aceptados y rechazados por umbral, y la nitidez de las muestras;
  - dónde vive el código: en el simulador, en el servidor o en `scripts/`. Si toca `servidor/`, se hace con la revisión de B.
- Las fotos y los recortes nunca salen de la memoria ni de `datos/`. El reporte lleva solo números, sin nombres de archivo que identifiquen a nadie fuera del equipo.

## Hacer

1. La medición que se acuerde, con sus pruebas:
   - Usan caras armadas o imágenes sintéticas, como las del servidor, y no fotos reales.
   - Corren en `simulador.yml` o en `servidor.yml`, según dónde viva el código.
   - Sin fotos reales se saltan, como `test_caras_reales.py`.
2. La medición con los tres integrantes (20 intentos cada uno) y los impostores.
3. El umbral:
   - el valor que no acepta a ningún impostor y rechaza a lo sumo 2 de 20 por persona;
   - si ninguno cumple las dos condiciones, gana no aceptar impostores, y se anota el costo en rechazos.
4. `NITIDEZ_MIN`, con la `calidad` de las muestras de inscripción (R7, paso 4): un valor que acepte las buenas y rechace las borrosas.
5. Anotar el resultado (RNF-07 · C2):
   - en `specs/decisiones.md`: el umbral, la nitidez, los aceptados y rechazados, el dataset y su licencia, el equipo y la fecha;
   - en `infra/.env.example`, los valores nuevos.
   - Si cambia el umbral de 0,363, también el ejemplo de R1 en `specs/reglas.md` y el valor por defecto de `servidor/accesia/config.py`, con la revisión de B, que es el dueño de ese archivo.
6. `simulador/README.md`, con cómo se calibra. En el paso 5 de `docs/guia-dia-de-clase.md`, cómo se recalibra en clase con los mismos comandos.

## No hacer

- No guardes recortes ni fotos fuera de `datos/`, ni los subas. El dataset de impostores tampoco va al repositorio.
- No cambies cómo funcionan R1 ni R7: solo sus valores.
- No toques `firmware/` ni `web/`.
- No uses la base del Compose compartido para medir, si eso crea llegadas o alertas.

## Criterios de aceptación

- C1 (RNF-07 · C1) Medidos los 3 × 20 intentos y los impostores, con los recortes del modo «como la cámara».
- C2 (RNF-07 · C2) El umbral y la nitidez elegidos quedan en `decisiones.md` y en `infra/.env.example`, y R1 queda al día si el umbral cambió.
- C3 (RNF-01 · C1 y C2) Ni la medición ni sus pruebas escriben imágenes fuera de `datos/`, y nada de `datos/` entra a Git.
- C4 (RNF-06 · C3) `simulador.yml` o `servidor.yml` en verde, con las pruebas nuevas marcadas.
- C5 `simulador/README.md`, la guía del día de clase y la bitácora al día.

## Al terminar

- Resume:
  - cómo mediste;
  - el umbral y la nitidez elegidos, con sus números;
  - el dataset de impostores y su licencia;
  - qué pruebas corriste, con su resultado.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-a`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
