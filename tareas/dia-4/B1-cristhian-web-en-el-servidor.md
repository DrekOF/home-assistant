<!--
Nombre: B1-cristhian-web-en-el-servidor.md
Descripción: Tarea B1 del Día 4 del frente B: la imagen del servidor trae la web compilada y el servidor la sirve en la raíz (D-04), para que la demo, el kit y el ensayo no necesiten Node.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 4 · Frente B · B1 · La web servida por el servidor

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/web-en-el-servidor`
- Depende de:
  - nada: es la primera tarea de B hoy, porque el kit (C1) arma la imagen del servidor con ella;
  - las pantallas de C1 y C2 del Día 3 entran solas a la imagen cuando están en `main`.
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/arquitectura.md`, Piezas (la web, «servida por el servidor») y Servicios de Docker Compose (la imagen con la raíz como contexto);
  - de `specs/decisiones.md`, D-04;
  - `web/README.md` (cómo compila y el simulacro) y `servidor/README.md`.

## Objetivo

La imagen del servidor trae la web compilada, y el servidor la sirve en la raíz, como dicen D-04 y `arquitectura.md`. Con el Compose arriba, `http://localhost:8000` abre la web. La demo, el kit y el ensayo no necesitan Node ni `npm run dev`.

## Antes de empezar

- Propón en el plan:
  - **La etapa que compila la web** en `servidor/Dockerfile`: Node 22, `npm ci` y `npm run build`. Como el resultado no depende de la arquitectura, va con `--platform=$BUILDPLATFORM`, como la de los modelos.
  - **Cómo sirve el servidor la web:**
    - los archivos de `dist/` en la raíz;
    - cualquier ruta que no empiece por `/api/` ni sea un archivo devuelve `index.html`, porque la web usa rutas del navegador;
    - `/api/…` no cambia: una ruta que no existe sigue respondiendo 404 con el esquema `Error`.
  - **El simulacro:** que la web compilada no lleve MSW ni `mockServiceWorker.js`, que quedó pendiente desde la C del Día 1.
  - **La caché:** larga para los archivos con hash, ninguna para `index.html`.
  - **Sin web compilada** (en el PC con `uv run uvicorn`, o en las pruebas): el servidor arranca igual y lo dice en el registro.
  - **Las pruebas:** cómo se prueba sin compilar la web en cada corrida de pytest, por ejemplo con una carpeta `dist` mínima.
- No hace falta cambiar `openapi.yaml`: la web no es parte de la API.

## Hacer

1. La etapa de la web en el `Dockerfile`, y lo que haga falta en `.dockerignore` (por ejemplo, `web/node_modules`).
2. El servidor sirve la web, con la ruta de respaldo a `index.html` y `/api` intacto.
3. Pruebas, cada una con su marca, por ejemplo `D-04 · web servida`:
   - la raíz devuelve `index.html`;
   - un archivo de la web se sirve con su tipo y su caché;
   - una ruta del navegador, recargada, devuelve `index.html`;
   - `/api/v1/no-existe` sigue siendo 404 con `Error`, y `GET /api/v1/salud` no cambia;
   - sin `dist`, el servidor arranca y la API responde.
4. La imagen:
   - se construye con `docker buildx build --platform linux/amd64,linux/arm64`, como en B2 del Día 2, y la etapa de la web corre una vez;
   - no lleva el simulacro;
   - `docker compose -f infra/compose.yaml config` sigue en orden.
5. Documentación:
   - `servidor/README.md` y `web/README.md`: cómo se abre la web en el Compose;
   - `CLAUDE.md`: el comando o la dirección;
   - `specs/arquitectura.md`: quitar el «más adelante» de la web compilada;
   - la bitácora.

## No hacer

- No cambies las rutas de `/api` ni `openapi.yaml`.
- No toques las pantallas de la web: son de C.
- No subas `dist/` al repositorio.
- No reconstruyas el Compose de la carpeta principal sin preguntar (acuerdos del 00).

## Criterios de aceptación

- C1 (D-04; RF-09 · C1) Con el Compose arriba, `http://localhost:8000` abre la web, con su inicio de sesión y sus pantallas, sin Node.
- C2 Recargar una ruta de la web sigue funcionando, y `/api` responde igual que antes, con sus errores.
- C3 La imagen no lleva el simulacro.
- C4 (RNF-04 · C1) La imagen se sigue construyendo para amd64 y arm64.
- C5 (RNF-06 · C3) `servidor.yml` y `web.yml` en verde; `servidor/README.md`, `web/README.md`, `arquitectura.md`, `CLAUDE.md` y la bitácora al día.

## Al terminar

- Resume:
  - cómo se compila la web en la imagen y cómo la sirve el servidor;
  - qué pruebas corriste, con su resultado por marca;
  - el tamaño de la imagen antes y después.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con todos los workflows del PR en verde. Cuando esté en `main`, avisa a C, que arma las imágenes del kit (C1).
- El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
