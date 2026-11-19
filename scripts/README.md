<!--
Nombre: README.md
Descripción: Utilidades del repositorio de AccesIA.
Fecha de creación: 2026-11-11
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.2
-->

# Scripts

Utilidades del repositorio, en versión PowerShell (`.ps1`, Windows) y Bash (`.sh`, Linux y Raspberry).

| Script | Qué hace | Lo crea |
| --- | --- | --- |
| `preparar-skills` | Trae los skills de frontend a `.claude/skills/` en commits fijos | Tarea C del Día 1 |
| `empaquetar-complementos.ps1` | Arma `kit/complementos/` con los dos complementos de Home Assistant OS, listos para copiar a la Pi (D-22). Solo en PowerShell; en Linux, con `pwsh`, como en la CI. Detalle en `complementos/README.md` | Tarea B4 del Día 4 |

Los scripts de Docker y del kit están en `infra/scripts/`.

## preparar-skills

Trae los seis skills de frontend (taste-skill, impeccable, los de Emil Kowalski, frontend-design, refactoring-ui y web-design-guidelines) y la copia local de las reglas de web-design-guidelines: `command.md`, de `vercel-labs/web-interface-guidelines`, que queda en `.claude/skills/web-design-guidelines/command.md`.

Desde la raíz del repositorio, en PowerShell:

```powershell
.\scripts\preparar-skills.ps1
```

En Linux, en la Raspberry o en Git Bash:

```bash
./scripts/preparar-skills.sh
```

- Cada repositorio se trae en el commit que anota la tabla del inicio del script, que es la misma en los dos. Sin opciones, el script nunca cambia de commit: todo el equipo tiene los mismos skills.
- Descarga solo la carpeta que necesita de cada repositorio, así que tarda unos 20 segundos.
- Se puede correr varias veces: reemplaza lo que instaló antes y anota en `.claude/skills/VERSIONES.txt` el commit de cada carpeta.
- Solo copia archivos: no corre nada de lo que trae. De impeccable se usan solo sus guías (`CLAUDE.md`, sección Web).
- Si algo falla (sin conexión, un commit que ya no existe o una ruta que cambió), no toca `.claude/skills/`, muestra el resumen y sale con código 1. Si una ruta cambió, muestra dónde están ahora las carpetas con `SKILL.md` y no copia nada a ciegas.
- `.claude/skills/` está en `.gitignore`: cada integrante corre el script en su equipo y después reinicia Claude Code para que cargue los skills.

Para pasar a versiones nuevas, `-Actualizar` (PowerShell) o `--actualizar` (Bash) consulta el último commit de cada repositorio, muestra cuáles cambiaron, trae esa versión y, si todo sale bien, anota los commits nuevos en la tabla de los dos scripts. Ese cambio se revisa con `git diff scripts/` y se sube en un PR. Si cambia el commit de `web-interface-guidelines`, se actualiza también el que nombra `CLAUDE.md`.

Si Windows responde que la ejecución de scripts está deshabilitada, córrelo así, solo esa vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\preparar-skills.ps1
```
