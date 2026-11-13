<!--
Nombre: README.md
Descripción: Cómo se trabajan las tareas de AccesIA con Claude Code, orden y plantilla.
Fecha de creación: 2026-11-11
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.4
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
- Día 3: primero el Hito 1 del Día 2, apenas se fusione la C del Día 2. B1 empieza primero, porque B2 y B3 la necesitan; A1, C1 y la primera parte de C2 van en paralelo. Desde el Hito 1, Docker Compose corre solo desde la carpeta principal, en `main`. Las dependencias, el reparto entre tres sesiones y el guion del Hito 2 están en `dia-3/00-todos-orden-e-hito-2.md`.
- Día 4: primero el Hito 1. Con D-22, la demo pasa a la Raspberry Pi, y B4 (los complementos de la base y del servidor) va primero en la sesión B: el Hito 2, la evaluación de B3, C2 del Día 3 y el kit (C1) la necesitan. El Hito 2 se hace en clase con la B4 y C2 del Día 3; si no alcanzan, MQTT y Home Assistant se prueban con el escenario 2 y el agente espera a la B4. Lo que necesita la placa o la Pi pasa al día de clase si el hardware solo está allá. Lo que debe quedar listo para el ensayo del Día 5 está en `dia-4/00-todos-orden-y-listo-para-el-ensayo.md`.
- Si una misma persona ejecuta varias tareas el mismo día, este orden evita bloqueos: B, C y A el Día 1; B1, B2, A y C el Día 2; B1, B2, B3, A1, C1, C2 y A2 el Día 3; B4, B2, B3, A1, A3, A2, C1 y C2 el Día 4.
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

## Tareas del Día 3

| Archivo | Responsable | Rama |
| --- | --- | --- |
| [dia-3/00-todos-orden-e-hito-2.md](dia-3/00-todos-orden-e-hito-2.md) | Todos | `b/hito-2` (solo el resultado del hito) |
| [dia-3/A1-julian-puerta-del-simulador.md](dia-3/A1-julian-puerta-del-simulador.md) | Julián Andrés Silva Morales | `a/puerta-simulador` |
| [dia-3/A2-julian-camara-de-la-placa.md](dia-3/A2-julian-camara-de-la-placa.md) | Julián Andrés Silva Morales | `a/camara-placa` |
| [dia-3/B1-cristhian-asistencia-y-consultas.md](dia-3/B1-cristhian-asistencia-y-consultas.md) | Cristhian Eduardo Sánchez Mosquera | `b/asistencia` |
| [dia-3/B2-cristhian-mqtt.md](dia-3/B2-cristhian-mqtt.md) | Cristhian Eduardo Sánchez Mosquera | `b/mqtt` |
| [dia-3/B3-cristhian-mcp-y-semilla.md](dia-3/B3-cristhian-mcp-y-semilla.md) | Cristhian Eduardo Sánchez Mosquera | `b/mcp-agente` |
| [dia-3/C1-jhon-accesos-asistencia-y-horarios.md](dia-3/C1-jhon-accesos-asistencia-y-horarios.md) | Jhon Jairo Perdomo Perdomo | `c/accesos-asistencia-horarios` |
| [dia-3/C2-jhon-home-assistant-y-agente.md](dia-3/C2-jhon-home-assistant-y-agente.md) | Jhon Jairo Perdomo Perdomo | `c/home-assistant` |

## Tareas del Día 4

| Archivo | Responsable | Rama |
| --- | --- | --- |
| [dia-4/00-todos-orden-y-listo-para-el-ensayo.md](dia-4/00-todos-orden-y-listo-para-el-ensayo.md) | Todos | — |
| [dia-4/A1-julian-calibracion-del-umbral.md](dia-4/A1-julian-calibracion-del-umbral.md) | Julián Andrés Silva Morales | `a/calibracion` |
| [dia-4/A2-julian-placa-con-home-assistant.md](dia-4/A2-julian-placa-con-home-assistant.md) | Julián Andrés Silva Morales | `a/placa-home-assistant` |
| [dia-4/A3-julian-ip-de-la-pi.md](dia-4/A3-julian-ip-de-la-pi.md) | Julián Andrés Silva Morales | `a/ip-de-la-pi` |
| [dia-4/B1-cristhian-web-en-el-servidor.md](dia-4/B1-cristhian-web-en-el-servidor.md) | Cristhian Eduardo Sánchez Mosquera | `b/web-en-el-servidor` |
| [dia-4/B2-cristhian-modo-extraer.md](dia-4/B2-cristhian-modo-extraer.md) | Cristhian Eduardo Sánchez Mosquera | `b/modo-extraer` |
| [dia-4/B3-cristhian-evaluacion-del-agente-y-cobertura.md](dia-4/B3-cristhian-evaluacion-del-agente-y-cobertura.md) | Cristhian Eduardo Sánchez Mosquera | `b/evaluacion-agente` |
| [dia-4/B4-cristhian-complementos-de-la-base-y-del-servidor.md](dia-4/B4-cristhian-complementos-de-la-base-y-del-servidor.md) | Cristhian Eduardo Sánchez Mosquera | `b/complementos` |
| [dia-4/C1-jhon-kit-del-dia-de-clase.md](dia-4/C1-jhon-kit-del-dia-de-clase.md) | Jhon Jairo Perdomo Perdomo | `c/kit` |
| [dia-4/C2-jhon-playwright-y-arm64.md](dia-4/C2-jhon-playwright-y-arm64.md) | Jhon Jairo Perdomo Perdomo | `c/playwright-y-arm64` |

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
