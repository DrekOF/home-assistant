<!--
Nombre: C2-jhon-playwright-y-arm64.md
Descripción: Tarea C2 del Día 4 del frente C: Playwright recorre toda la web en la CI (RF-09 · C3) y las imágenes arm64 del plan C quedan probadas con emulación (RNF-04 · C1). Con D-22, los complementos los prueba B4 en arm64.
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.1
-->

# Día 4 · Frente C · C2 · Playwright en la CI y arm64

- Responsable: Jhon Jairo Perdomo Perdomo (frente C)
- Rama: `c/playwright-y-arm64`
- Depende de:
  - para Playwright: C1 del Día 3 en `main`, con todas las pantallas;
  - para arm64: nada. Con D-22, B4 prueba los complementos en arm64, en la CI y en el portátil; aquí quedan las imágenes del plan C. La imagen del servidor ya trae la web (B1, en `main`).
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/requisitos.md`: RF-09 y RNF-04;
  - de `specs/decisiones.md`: D-04, D-11, D-21 y D-22, con «Lo que cambia en las decisiones anteriores con D-22» (las imágenes arm64 vuelven a hacer falta);
  - de `specs/arquitectura.md`: «Cómo se prueban sin la Pi»;
  - `web/README.md` y `web/DESIGN.md`;
  - `.github/workflows/web.yml`;
  - de `servidor/README.md`: Modelos de cara (la imagen multiarquitectura).

## Objetivo

- Playwright recorre toda la web con el simulacro en `web.yml`, en cada PR (RF-09 · C3). Llevarlo a la CI quedó pendiente desde la C del Día 1.
- Las imágenes arm64 del plan C, el escenario 1 (el servidor y los servicios del Compose), arrancan con emulación (RNF-04 · C1). Con D-22, los complementos los prueba B4.

## Antes de empezar

- Si no tienes los skills, corre `.\scripts\preparar-skills.ps1` y reinicia Claude Code. Se usan los seis: web-design-guidelines con su copia local `command.md`, y de impeccable solo sus guías.
- Propón en el plan:
  - **Qué recorre Playwright:** cada pantalla (inicio de sesión, Personas, Inscripción, Cámaras, Accesos, Asistencia, Horarios y la ficha de la persona), con los errores del contrato que ya cubre el simulacro.
  - **Cómo corre en `web.yml`:** el navegador en caché, el informe como artefacto si algo falla, y cuánto tiempo suma a la CI.
  - **Qué se prueba en arm64 y dónde:**
    - por ejemplo, con Docker Desktop y QEMU en el portátil: que el servidor arranca y carga los modelos, PostgreSQL con pgvector, Mosquitto y Ollama;
    - qué no repite de B4, que ya construye los complementos para arm64 en `complementos.yml`;
    - si además va a la CI, y cuánto tarda.

## Hacer

1. Playwright con el simulacro, en `web.yml`:
   - las pruebas de las pantallas que falten, cada una nombrada con su criterio;
   - las capturas a 1280×720 y 1440×900, revisadas.
2. Una revisión final de la web:
   - de accesibilidad, con la copia local de `.claude/skills/web-design-guidelines/command.md`;
   - de diseño, con los skills.
   - Lo que se corrija va con su prueba.
3. arm64:
   - construir con `docker buildx build --platform linux/amd64,linux/arm64`;
   - arrancar con emulación cada imagen que usa el escenario 1 (plan C), con lo que se compruebe en cada una;
   - anotar los tiempos.
4. `web/README.md` (Playwright en la CI), `infra/README.md` (arm64) y la bitácora.

## No hacer

- No cambies las pantallas por gusto: solo lo que pidan la revisión o una prueba.
- No escribas los tipos a mano: se generan con `npm run tipos`.
- No toques `servidor/`, los complementos, `firmware/` ni `simulador/`. Si arm64 encuentra un problema de la imagen del servidor, se le avisa a B.
- No subas las imágenes, las capturas ni el informe de Playwright.

## Criterios de aceptación

- C1 (RF-09 · C3) Playwright recorre todas las pantallas en `web.yml`, en verde.
- C2 (RF-09 · C2 y C4) Las pantallas de RF-09 · C2 funcionan con el simulacro, en español y con la hora de Colombia, y las capturas están revisadas.
- C3 (RNF-04 · C1) Las imágenes arm64 del plan C (escenario 1) arrancan con emulación, con el resultado anotado.
- C4 (RNF-06 · C3) `web.yml` en verde; `web/README.md`, `infra/README.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué recorre Playwright y cuánto suma a la CI;
  - qué encontró la revisión final y qué se corrigió;
  - el resultado de arm64, con sus tiempos.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-c`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
