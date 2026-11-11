<!--
Nombre: C-jhon-skills-y-web.md
Descripción: Tarea del Día 1 del frente C: skills de frontend y web base con inicio de sesión y Personas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 1 · Frente C · Skills de frontend y web base

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/skills-y-web`
- Lee primero: `CLAUDE.md` (sección Web); `specs/requisitos.md` (RF-02 y RF-09); `specs/consentimiento.md`; `specs/contratos/openapi.yaml`; `specs/decisiones.md` (D-07 y D-11).

## Objetivo

Dejar los skills de frontend listos para todo el equipo y una web con inicio de sesión y Personas que funcione contra un simulacro de la API generado desde el contrato.

## Hacer

1. Skills de frontend:
   - `scripts/preparar-skills.ps1` y `scripts/preparar-skills.sh` clonan cada repositorio (`git clone --depth 1`) en una carpeta temporal y copian a `.claude/skills/`:

     | Repositorio | Qué se copia |
     | --- | --- |
     | `https://github.com/Leonxlnx/taste-skill` | `skills/taste-skill`, completo |
     | `https://github.com/pbakaus/impeccable` | `.claude/skills/impeccable` |
     | `https://github.com/emilkowalski/skills` | Todas las carpetas de `skills/` |
     | `https://github.com/anthropics/skills` | `skills/frontend-design` |

   - Si una ruta cambió, el script busca la carpeta que tiene `SKILL.md`, avisa y no copia a ciegas.
   - Se puede correr varias veces: reemplaza lo anterior, anota en `.claude/skills/VERSIONES.txt` el commit de cada repositorio y muestra un resumen.
   - `.claude/skills/` está en `.gitignore`: cada integrante corre el script y reinicia Claude Code para que cargue los skills.
2. Web base en `web/`:
   - React + Vite + TypeScript, con React Router, TanStack Query y `openapi-fetch`. Los tipos los genera `openapi-typescript` desde `specs/contratos/openapi.yaml` (`npm run tipos`).
   - Simulacro de la API con MSW, activable con `VITE_SIMULACRO=1`, con datos de ejemplo coherentes con el contrato.
   - En desarrollo, Vite envía `/api` a `http://localhost:8000`.
   - Pantallas:
     - Inicio de sesión.
     - Personas: lista con búsqueda y paginación, crear, editar, activar y desactivar.
     - Ficha de la persona con su consentimiento: el texto viene de la API (`specs/consentimiento.md`), dice que es opcional, ofrece el registro manual como alternativa, y permite registrarlo y revocarlo con confirmación.
   - Navegación con Personas, Inscripción, Accesos, Asistencia y Cámaras. Las que aún no existen muestran «Próximamente».
   - Diseño con los skills (taste completo, impeccable, Emil Kowalski y frontend-design). Antes de diseñar, propón una dirección visual corta (tipografía, color y densidad) y espera confirmación.
   - Textos en español; fechas y horas con `es-CO` y `America/Bogota`.
   - Accesibilidad: etiquetas en los formularios, foco visible, todo usable con teclado y contraste AA.
3. Pruebas:
   - Vitest para la lógica (formato de fechas y validaciones).
   - Playwright con el simulacro: iniciar sesión, crear una persona, registrar su consentimiento y comprobar que «Inscribir» solo se habilita con consentimiento vigente.
   - Al terminar cada pantalla, Playwright toma capturas y Claude Code las revisa: que se vea y funcione como se planeó.
4. `web/README.md` con los comandos.

## No hacer

- No escribas tipos de la API a mano: salen de `openapi.yaml`.
- Antes de agregar una librería de componentes, pregunta.
- No guardes fotos ni datos personales en el navegador.

## Criterios de aceptación

- C1 Los scripts dejan los skills en `.claude/skills/`, en Windows y en Linux.
- C2 `npm run dev` con el simulacro muestra el inicio de sesión y Personas funcionando.
- C3 (RF-02 · C3 y C4) El consentimiento muestra su texto y el aviso; «Inscribir» está deshabilitado sin consentimiento vigente.
- C4 (RF-09 · C3 y C4) Playwright en verde, capturas revisadas y textos en español.
- C5 `npm run tipos` regenera los tipos sin cambios a mano y `npm run build` pasa.
- C6 La bitácora y `web/README.md` están al día.

## Al terminar

- Resume qué hiciste, qué pruebas corriste y su resultado, y la dirección visual elegida.
- PR a `main` con los criterios cumplidos.
