<!--
Nombre: README.md
Descripción: Cómo se trabajan las tareas de AccesIA con Claude Code, orden y plantilla.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
-->

# Tareas

Cada tarea es un archivo que se le pasa a Claude Code. Dice quién es el responsable, qué leer, qué construir, qué no tocar y cómo saber que está terminada.

## Cómo se trabaja una tarea

1. Desde `main` actualizado, abre Claude Code en la raíz del repositorio.
2. Pégale este mensaje, cambiando el archivo de la tarea:

   ```text
   Lee CLAUDE.md y tareas/dia-1/B-cristhian-compose-y-base.md, y las specs que nombra. Crea la rama que indica la tarea. Antes de escribir código, propón un plan corto y espera mi confirmación.
   ```

3. Revisa el plan, confírmalo o corrígelo, y deja que avance. Cuando proponga algo grande, revísalo antes de aceptar.
4. Al final, Claude Code corre las pruebas, actualiza la bitácora y resume lo que hizo. Revisa el resumen y el diff.
5. Haz el commit y el PR desde tu cuenta. Con las pruebas en verde, se fusiona.

## Orden

- Día 1: primero la tarea 00, los tres juntos. Después A, B y C en paralelo, cada una en su rama.
- Día 2: A, B1 y C empiezan en paralelo; B2 sale de `main` cuando B1 está fusionada. El orden y el guion del Hito 1 están en `dia-2/00-todos-orden-e-hito-1.md`.
- Si una misma persona ejecuta varias tareas el mismo día, este orden evita bloqueos: B, C y A el Día 1; B1, B2, A y C el Día 2.
- Las tareas de cada día se escriben al cerrar el día anterior, a partir de `specs/plan.md` y de lo aprendido.

## Tareas del Día 1

| Archivo | Responsable | Rama |
| --- | --- | --- |
| [dia-1/00-todos-acordar-contratos.md](dia-1/00-todos-acordar-contratos.md) | Todos | — |
| [dia-1/A-julian-esp-idf-y-deteccion.md](dia-1/A-julian-esp-idf-y-deteccion.md) | Julián Andrés Silva Morales | `a/esp-idf-deteccion` |
| [dia-1/B-cristhian-compose-y-base.md](dia-1/B-cristhian-compose-y-base.md) | Cristhian Eduardo Sánchez Mosquera | `b/compose-y-base` |
| [dia-1/C-jhon-skills-y-web.md](dia-1/C-jhon-skills-y-web.md) | Jhon Jairo Perdomo Perdomo | `c/skills-y-web` |

## Tareas del Día 2

| Archivo | Responsable | Rama |
| --- | --- | --- |
| [dia-2/00-todos-orden-e-hito-1.md](dia-2/00-todos-orden-e-hito-1.md) | Todos | `b/hito-1` (solo el resultado del hito) |
| [dia-2/A-julian-simulador.md](dia-2/A-julian-simulador.md) | Julián Andrés Silva Morales | `a/simulador` |
| [dia-2/B1-cristhian-sesion-y-api.md](dia-2/B1-cristhian-sesion-y-api.md) | Cristhian Eduardo Sánchez Mosquera | `b/sesion-y-api` |
| [dia-2/B2-cristhian-reconocimiento-e-inscripcion.md](dia-2/B2-cristhian-reconocimiento-e-inscripcion.md) | Cristhian Eduardo Sánchez Mosquera | `b/reconocimiento` |
| [dia-2/C-jhon-inscripcion-y-camaras.md](dia-2/C-jhon-inscripcion-y-camaras.md) | Jhon Jairo Perdomo Perdomo | `c/inscripcion-y-camaras` |

## Plantilla de una tarea

```markdown
# Día N · Frente X · Título

- Responsable:
- Rama:
- Lee primero:

## Objetivo
Una o dos frases: qué queda funcionando al terminar.

## Hacer
Pasos concretos, con archivos y carpetas.

## No hacer
Límites: lo que es de otro día, de otro frente o de un contrato.

## Criterios de aceptación
C1, C2… con el requisito o la regla que cumplen (por ejemplo, RF-04 · C2).

## Al terminar
Resumen, pruebas, bitácora y PR.
```
