<!--
Nombre: C1-jhon-accesos-asistencia-y-horarios.md
Descripción: Tarea C1 del Día 3 del frente C: pantallas Accesos, Asistencia (con el registro manual) y Horarios, y lo que la ficha de la persona muestra de sus datos (RF-12).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Frente C · C1 · Accesos, Asistencia y Horarios

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/accesos-asistencia-horarios`
- Depende de:
  - la tarea C del Día 2 (`c/inscripcion-y-camaras`) fusionada, porque esta sale de `main` con ella;
  - B1 del Día 3 en `main`, para probar Accesos, Asistencia y la ficha contra el servidor real. Antes se trabaja contra el simulacro.
  - La API de horarios ya está en `main` (B1 del Día 2).
- Lee primero: `CLAUDE.md` (sección Web); `tareas/dia-3/00-todos-orden-e-hito-2.md`; `web/README.md` y `web/DESIGN.md`; `specs/requisitos.md` (RF-05 · C3, RF-06, RF-09, RF-12 · C1 y C3, RF-13); `specs/reglas.md` (R5 y R8); `specs/contratos/openapi.yaml` (Accesos, Asistencia, Rostros y Horarios, con sus esquemas); `specs/decisiones.md` (D-07 y D-20).

## Objetivo

La web suma tres pantallas:

- Accesos: los eventos con filtros;
- Asistencia: el reporte del día, con el botón de registro manual;
- Horarios: los bloques por día.

La ficha de la persona muestra sus muestras, sus accesos y su asistencia, con el botón para borrar sus huellas. Primero se hace contra el simulacro y después contra el servidor real.

## Antes de empezar

- Si no tienes los skills, corre `.\scripts\preparar-skills.ps1` y reinicia Claude Code. Se usan los seis: web-design-guidelines con su copia local `command.md`, y de impeccable solo sus guías.
- Trae `main` con la tarea C del Día 2. Si B1 del Día 3 cambió `openapi.yaml`, corre `npm run tipos`; los tipos no se escriben a mano.
- Propón en el plan:
  - cómo se ven las tres pantallas y la parte nueva de la ficha, apoyado en `web/DESIGN.md` y en los skills;
  - el formulario de Horarios, con un renglón por día (activo, hora y tolerancia, RF-13 · C5).
  - Espera confirmación.

## Hacer

1. Simulacro al día (MSW):
   - suma `GET /api/v1/accesos`, `GET` y `POST /api/v1/asistencia`, `GET /api/v1/personas/{persona_id}/asistencia` y las rutas de rostros, con los errores del contrato;
   - el registro manual del simulacro aplica R5 con los horarios del simulacro;
   - sus pruebas de Vitest comprueban que responde como dice `openapi.yaml`.
2. Pantalla Accesos (RF-05 · C3):
   - filtros por fechas, resultado, persona y cámara;
   - paginación del contrato (`pagina` y `por_pagina`), del más reciente al más antiguo;
   - la hora en `es-CO` y `America/Bogota` (R8); un `desconocido` sin persona.
   - Los filtros quedan en la dirección, para volver a la misma vista al recargar.
3. Pantalla Asistencia (RF-06 · C3 y C5):
   - el reporte de una fecha (hoy por defecto), con a tiempo, tarde (con los minutos), sin horario y ausentes, y el total;
   - las llegadas manuales se distinguen y dicen quién las registró.
   - Botón «Registrar llegada»:
     - pide la persona y la hora, que no puede ser futura;
     - errores: 409 `asistencia_duplicada` (ya tiene llegada ese día), 404 y 422 junto al campo que falló.
     - Es la alternativa para quien no dio consentimiento (RF-02 · C3).
4. Pantalla Horarios (RF-13 · C1, C2, C3 y C5):
   - la lista;
   - crear, editar y borrar, con el formulario de un renglón por día;
   - editar reemplaza la lista de bloques;
   - errores: 409 `horario_en_uso`, 409 `nombre_duplicado` y 422 junto al campo que falló.
5. Ficha de la persona (RF-12 · C1 y C3):
   - cuántas muestras tiene y el botón «Borrar huellas», con una confirmación que dice que no se puede deshacer;
   - sus últimos accesos y su asistencia, con enlace a las pantallas completas.
   - Si no alcanza el día, esta parte pasa al Día 4 y se anota en la bitácora.
6. Navegación: Accesos, Asistencia y Horarios dejan de mostrar «Próximamente». Actualiza las pruebas de Playwright que esperaban esa pantalla.
7. Pruebas:
   - Vitest: los textos de cada estado, la validación de la hora de la llegada manual y de los bloques, y el simulacro contra el contrato.
   - Playwright con el simulacro, cada prueba nombrada con su criterio:
     - filtrar accesos;
     - ver el reporte y registrar una llegada manual, también el 409;
     - crear, editar y borrar un horario, también `horario_en_uso`;
     - borrar las huellas desde la ficha.
   - Playwright contra el servidor real (`npm run e2e:servidor`, con el Compose arriba y avisándole a la sesión de B): las mismas pantallas con datos que se crean y se borran al final. Las credenciales salen de `infra/.env`, nunca del código.
   - Capturas de las pantallas nuevas a 1280×720 y 1440×900, revisadas.
   - Revisión de accesibilidad con la copia local de `.claude/skills/web-design-guidelines/command.md`.
8. `web/README.md` y `web/DESIGN.md` (componentes nuevos).

## No hacer

- No cambies el servidor ni los contratos. Si la API no cumple el contrato, avísale a B con el caso exacto (ruta, cuerpo y respuesta).
- No escribas tipos de la API a mano.
- No guardes datos personales ni tokens en el navegador.
- Home Assistant es de C2.
- Antes de agregar una librería, pregunta. El ejecutable de impeccable no se descarga ni se corre sin preguntarle al equipo.

## Criterios de aceptación

- C1 (RF-05 · C3) Accesos filtra y pagina como dice el contrato.
- C2 (RF-06 · C3 y C5) Asistencia muestra el reporte del día con ausentes y registra llegadas a mano con sus errores.
- C3 (RF-13 · C1 a C3 y C5) Horarios crea, edita y borra, con un renglón por día y el 409 `horario_en_uso`.
- C4 (RF-12 · C1 y C3) La ficha muestra muestras, accesos y asistencia, y borra las huellas; o queda anotado que pasa al Día 4.
- C5 (RF-09) Playwright con el simulacro en verde, Playwright contra el servidor real en verde con B1 en `main`, capturas revisadas, textos en español y horas en `es-CO` y `America/Bogota`.
- C6 (RNF-06 · C3) `npm run build` y `npm test` en verde, `npm run tipos` sin cambios y todos los workflows del PR en verde.
- C7 `web/README.md`, `web/DESIGN.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué hiciste y qué pruebas corriste, con su resultado;
  - las decisiones de diseño;
  - qué se probó contra el servidor real y qué falta.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-c`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
