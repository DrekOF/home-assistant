<!--
Nombre: C-jhon-inscripcion-y-camaras.md
Descripción: Tarea del Día 2 del frente C: Personas y consentimiento contra la API real, y pantallas Inscripción y Cámaras.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 2 · Frente C · API real, Inscripción y Cámaras

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/inscripcion-y-camaras`
- Lee primero: `CLAUDE.md` (sección Web); `tareas/dia-2/00-todos-orden-e-hito-1.md`; `web/README.md` y `web/DESIGN.md`; `specs/requisitos.md` (RF-02, RF-03, RF-09 y RF-10); `specs/reglas.md` (R7 y R9); `specs/contratos/openapi.yaml` (Sesión, Personas, Consentimiento, Inscripciones y Cámaras, con sus esquemas); `specs/decisiones.md` (D-07, D-11 y D-13).

## Objetivo

Personas y consentimiento funcionan contra el servidor real. La web suma la pantalla Inscripción, con el avance en vivo («Muestra 3 de 5») y el motivo del último rechazo, y la pantalla Cámaras, con el token que se muestra una sola vez.

## Antes de empezar

- Si no tienes los skills, corre `.\scripts\preparar-skills.ps1` y reinicia Claude Code. Se usan los seis; web-design-guidelines, con su copia local `command.md`, y de impeccable solo sus guías.
- Las pantallas nuevas se hacen primero contra el simulacro. Se prueban contra el servidor real cuando B1 (sesión, personas, consentimiento y cámaras) y B2 (inscripción) estén en `main`.
- Cuando B1 llegue a `main`, actualiza tu rama: B1 ya regeneró `esquema.d.ts` con el contrato 1.3, así que `npm run tipos` no debe dejar cambios.
- Propón en el plan cómo se ven las dos pantallas, apoyado en `web/DESIGN.md` y en los skills, y espera confirmación.

## Hacer

1. Personas y consentimiento contra la API real (RF-02, RF-09 · C1):
   - Con Compose arriba y `npm run dev`, recorre todo: entrar, buscar con y sin tildes, paginar, crear, editar, activar y desactivar, registrar el consentimiento (web y papel) y revocarlo. Corrige en la web lo que no funcione.
   - Si la API no cumple el contrato, no la cambies: avísale a B con el caso exacto (ruta, cuerpo y respuesta).
   - Playwright contra el servidor real, con una configuración aparte que no levanta el simulacro (por ejemplo `npm run e2e:servidor`) y que se corre a mano con Compose arriba.
     - Las credenciales salen de `infra/.env` (`ADMIN_CORREO` y `ADMIN_CLAVE_INICIAL`), nunca del código.
     - Las personas que crea usan documentos de prueba y se borran al final.
     - La CI sigue con el simulacro.
2. Simulacro al día (MSW):
   - Suma `/api/v1/dispositivos` (listar, crear, ver, editar y cambiar el token) y `/api/v1/inscripciones` (abrir, ver y cancelar), con los errores del contrato.
   - La inscripción del simulacro avanza sola cada pocos segundos, con algún rechazo, para ver la barra sin cámara.
   - Sus pruebas de Vitest comprueban que responde como dice `openapi.yaml`, igual que las del Día 1.
3. Pantalla Inscripción (RF-03 · C1, C5 y C6; R7; R9):
   - Se llega desde «Inscribir» en la ficha (`/inscripcion?persona=<id>`) o desde el menú. Se elige la persona (solo con consentimiento vigente) y la cámara (solo activas).
   - Abre la inscripción (`POST /api/v1/inscripciones`) y la consulta cada segundo (`GET /api/v1/inscripciones/{inscripcion_id}`) mientras siga `activa` (RF-03 · C6). El id queda en la dirección, para que al recargar siga mostrando la misma.
   - Muestra:
     - `BarraAvance` con «Muestra 3 de 5», usando `muestras` y `requeridas` de la API;
     - el tiempo que falta hasta `vence`;
     - el motivo del último rechazo en español, con qué hacer: un texto por cada valor de `MotivoMuestra` (por ejemplo, para `cara_pequena`, acercarse a la cámara).
   - Cancelar (`DELETE`), con confirmación.
   - Al terminar, dice cómo quedó: `completada` (con enlace a la ficha), `vencida` (las muestras aceptadas se conservan y se puede abrir otra) o `cancelada`.
   - Errores:
     - 422 `sin_consentimiento`;
     - 409 `inscripcion_activa`: la cámara ya tiene una. Vence sola a los 2 minutos; el contrato no tiene cómo encontrarla para cancelarla desde otra pestaña;
     - 404.
   - Accesibilidad: el avance y el motivo se anuncian cuando cambian, no cada segundo.
4. Pantalla Cámaras (RF-09 · C2; RF-10 · C1 a C3):
   - Lista con código, nombre, tipo, si está activa, si está en línea, modo (reconocer o inscribir) y último contacto en hora de Colombia. Se refresca sola cada pocos segundos.
   - Crear: código (`^[a-z0-9-]{3,32}$`, sin `servidor`), nombre, tipo y URL de captura, obligatoria si el tipo es `respaldo`.
   - Editar nombre, tipo y URL, y activar o desactivar.
   - Errores 409 `codigo_duplicado` y 422 junto al campo que falló.
   - Token:
     - Al crear la cámara, o al cambiar el token tras una confirmación que avisa que el anterior deja de servir, se muestra una sola vez en un diálogo, con botón para copiar y el aviso de que no se vuelve a ver.
     - El diálogo dice cómo usarlo: `token <token>` en la consola de la cámara, o la variable `TOKEN_CAMARA` en el simulador.
     - No va al caché de TanStack Query, ni al almacenamiento del navegador, ni a la dirección. Al cerrar el diálogo se olvida.
5. Navegación: Inscripción y Cámaras dejan de mostrar «Próximamente». Actualiza las pruebas de Playwright que esperaban esa pantalla (`e2e/personas.spec.ts` y `e2e/capturas.spec.ts`).
6. Pruebas:
   - Vitest: los textos de cada motivo, el tiempo que falta, la validación del código de cámara y el simulacro de cámaras e inscripciones contra el contrato.
   - Playwright con el simulacro, cada prueba nombrada con su criterio:
     - abrir una inscripción y ver «Muestra n de 5» hasta `completada`;
     - un rechazo con su motivo;
     - cancelar;
     - crear una cámara y ver el token una sola vez;
     - cambiar el token;
     - el código `servidor`, rechazado.
   - Capturas de las pantallas nuevas a 1280×720 y 1440×900, revisadas.
   - Revisión de accesibilidad con la copia local de `.claude/skills/web-design-guidelines/command.md`.
7. `web/README.md` (comandos y simulacro) y `web/DESIGN.md` (componentes nuevos).

## No hacer

- No cambies el servidor ni los contratos.
- No escribas tipos de la API a mano.
- No guardes el token, fotos ni datos personales en el navegador.
- Las pantallas Accesos, Asistencia y Horarios son del Día 3.
- Antes de agregar una librería, pregunta. El ejecutable de impeccable no se descarga ni se corre sin preguntarle al equipo.
- Los espacios duros van como ` `, que se ve en el código, como se decidió el Día 1.

## Criterios de aceptación

- C1 (RF-02 · C1 a C5; RF-09 · C1) Personas y consentimiento funcionan contra el servidor real, con Playwright contra el servidor en verde.
- C2 (RF-03 · C1, C5 y C6) Inscripción abre, muestra «Muestra n de 5» y el último motivo, y cancela: contra el simulacro y, con B2 en `main`, contra el servidor real.
- C3 (RF-10 · C1 a C3) Cámaras crea, edita, activa y desactiva, y cambia el token, que se muestra una sola vez.
- C4 (RF-09 · C2 a C4) Playwright con el simulacro en verde, capturas revisadas, textos en español y horas en `es-CO` y `America/Bogota`.
- C5 (RNF-06 · C3) `npm run build` y `npm test` en verde, `npm run tipos` sin cambios y `web.yml` en verde en el PR.
- C6 `web/README.md`, `web/DESIGN.md` y la bitácora al día.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado, las decisiones de diseño, qué se probó contra el servidor real y qué falta (por ejemplo, Inscripción contra el servidor real si B2 llegó tarde).
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-c`. Se fusiona con `web.yml` en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
