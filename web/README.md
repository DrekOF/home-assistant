<!--
Nombre: README.md
Descripción: Web de administración de AccesIA (frente C): comandos, simulacro, pruebas y estructura.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.3
-->

# Web de administración · frente C

React + Vite + TypeScript, servida por el servidor. Pantallas: Personas (con consentimiento), Inscripción, Accesos, Asistencia, Cámaras y Horarios. El Día 1 dejó listos el inicio de sesión, Personas y la ficha con el consentimiento; las demás muestran «Próximamente».

- Specs: `specs/requisitos.md` (RF-02, RF-03, RF-05, RF-06, RF-09, RF-10 y RF-13), `specs/consentimiento.md` y `specs/contratos/openapi.yaml`.
- Usa los seis skills de frontend de `.claude/skills/`: taste-skill, impeccable, los de Emil Kowalski, frontend-design, refactoring-ui y web-design-guidelines. Se traen con `scripts/preparar-skills.ps1` (o `.sh`). Se verifica con Playwright.
- Dirección visual que pidió el equipo: sobria y clara, tipo panel de trabajo, para verse en el portátil y en un proyector durante la demo, con movimiento sutil. Los tokens y los componentes están en `DESIGN.md`.
- La crea la tarea `tareas/dia-1/C-jhon-skills-y-web.md`.

## Comandos

Desde `web/`, en PowerShell. Necesita Node 22.22 o más reciente (la CI usa Node 24).

```powershell
npm ci                                  # instala las dependencias (la primera vez y cuando cambie package-lock.json)
npm run dev:simulacro                   # web en http://localhost:5173 con la API simulada: no necesita el servidor
npm run dev                             # web en http://localhost:5173; /api va al servidor en http://localhost:8000
npm run tipos                           # regenera src/api/esquema.d.ts desde specs/contratos/openapi.yaml
npm run build                           # revisa los tipos y compila en dist/
npm test                                # pruebas de la lógica y del simulacro con Vitest
npx playwright install chromium         # descarga el navegador de Playwright (una vez)
npm run e2e                             # pruebas de punta a punta con el simulacro; deja capturas en web/capturas/
```

`npm run e2e` levanta su propia web con el simulacro en el puerto 5174, así que no choca con una que ya esté abierta. Las capturas (1280×720 y 1440×900) quedan en `web/capturas/`, que Git ignora. El informe de Playwright queda en `web/playwright-report/`.

## Simulacro

Con `npm run dev:simulacro` (que activa `VITE_SIMULACRO=1` desde `.env.simulacro`), MSW responde la API dentro del navegador con datos de ejemplo coherentes con el contrato 1.2: personas ficticias, tres horarios por bloques, consentimientos vigentes y revocados, y los códigos de error del contrato.

- Entra con `admin@example.com` y la clave `simulacro`. La pantalla de entrada las muestra en modo simulacro. No existen en el servidor real.
- Todo vive en la memoria de la pestaña: al recargar, vuelve a los datos de ejemplo y pide entrar otra vez. No se guarda nada en el navegador.
- El texto del consentimiento se lee de `specs/consentimiento.md`, del bloque entre las dos líneas `---`, como lo hará el servidor.
- Las rutas que todavía no tienen pantalla responden 404 con el esquema `Error`.
- Sin `VITE_SIMULACRO=1`, el código y los datos del simulacro no entran al paquete de producción.

## Tipos de la API

`src/api/esquema.d.ts` lo genera `openapi-typescript`; no se edita a mano. La CI lo regenera y falla si quedó distinto de `openapi.yaml`. Dos detalles:

- Se genera con `--default-non-nullable false`, para que los campos con valor por defecto (`PersonaNueva.activa`, `ConsentimientoNuevo.medio`) sigan siendo opcionales, como en el contrato.
- La web usa TypeScript 5.9: `openapi-typescript` 7 pide TypeScript 5 y todavía no funciona con la 7.

## Estructura

```text
web/
├── src/
│   ├── api/            cliente de la API (openapi-fetch), tipos generados y consultas con TanStack Query
│   ├── componentes/    botones, campos, insignias, avisos, diálogo, esqueletos, barra de avance y marco
│   ├── estilos/        tokens.css y los estilos de componentes, marco y pantallas
│   ├── logica/         fechas en hora de Colombia, validaciones, horarios y texto, con sus pruebas
│   ├── pantallas/      inicio de sesión, Personas, formulario, ficha, consentimiento y Próximamente
│   └── simulacro/      MSW: datos de ejemplo, manejadores y su prueba contra el contrato
├── e2e/                pruebas de Playwright y capturas
├── public/             ícono y mockServiceWorker.js (lo genera MSW: no se edita)
└── DESIGN.md           sistema visual: tokens, componentes y qué skill apoya cada decisión
```

Si una herramienta pide la carpeta vacía para crear el proyecto, créalo en una carpeta temporal y mueve los archivos aquí. Este README se conserva y se completa.
