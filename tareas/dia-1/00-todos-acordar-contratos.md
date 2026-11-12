<!--
Nombre: 00-todos-acordar-contratos.md
Descripción: Tarea del Día 1 para los tres integrantes: revisar y acordar los contratos y crear el repositorio.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.1
-->

# Día 1 · Todos · Acordar los contratos

- Responsables: Julián, Cristhian y Jhon
- Duración: unos 45 minutos
- Rama: no hace falta; si cambia un contrato, el cambio va en una rama con prefijo `b/`, porque el frente B es el dueño de los contratos. Los acuerdos de esta reunión están en `b/contratos-v1-1`.

## Objetivo

Que los tres entiendan y acepten los contratos antes de programar. Desde ahí cada frente trabaja por su lado.

## Antes de la reunión: revisión con Claude Code

Uno de los tres le pide a Claude Code una revisión y la comparte con los demás:

```text
Lee CLAUDE.md, specs/README.md y todos los archivos de specs/ y specs/contratos/. No escribas código ni cambies archivos. Dime: 1) inconsistencias entre los contratos o con las specs, 2) huecos que impidan empezar las tareas del Día 1, 3) riesgos técnicos. Sé concreto: archivo, sección y propuesta.
```

La revisión quedó en `docs/revisiones/2026-11-11-revision-contratos-v1.md`. Sus acuerdos se aplicaron en la rama `b/contratos-v1-1`, con los contratos en versión 1.1; el detalle está en el registro de cambios de `specs/decisiones.md`.

## Pasos

1. (10 min) Leer `specs/README.md`, `specs/decisiones.md` (sobre todo D-12 a D-19, que son propuestas) y `specs/arquitectura.md`.
2. (20 min) Revisar cada contrato con quien lo usa:

   | Contrato | Lo revisan |
   | --- | --- |
   | `api-dispositivo.md` y `casos-recorte.json` | A y B |
   | `openapi.yaml` | B y C |
   | `mqtt.md` | A, B y C |
   | `mcp-agente.md` | B y C |
   | `base-de-datos.sql` | B |

3. (10 min) Resolver las preguntas abiertas y anotar lo acordado.
4. (5 min) Crear el repositorio privado, invitar a los tres y crear las etiquetas.

## Preguntas abiertas

1. Código y nombre de la cámara de la demo. Propuesta: `entrada`, «Entrada».
2. Hora real de la clase, para ajustar el horario de ejemplo (hoy: «Clase IA», lunes a viernes, 07:00, 10 minutos de tolerancia).
3. Correo de contacto del equipo para `specs/consentimiento.md`.
4. ¿Aceptan las decisiones D-12 a D-19? Los acuerdos de la revisión ya ajustaron D-16, D-17 y D-19; falta aceptar el conjunto.
5. ¿Se quedan las metas propuestas: tiempos de respuesta, 9 de 10 preguntas del agente y montaje en 45 minutos?

Preguntas que agregó la revisión (los números entre paréntesis son sus puntos):

6. ¿GitHub Pro con el Student Developer Pack o repo público? (2.1) **Resuelta:** repositorio privado sin proteger `main`; la regla de PR con pruebas en verde queda por disciplina.
7. ¿Qué pasa con la puerta en una repetición de R4? (1.7) **Resuelta:** un `permitido` repetido publica el evento con `repetido: true` y Home Assistant abre la puerta, sin guardar otro evento ni cambiar la asistencia. Un `denegado` repetido no publica nada.
8. ¿Binarios por tipo de PSRAM o por placa? (1.8) **Resuelta:** dos binarios, `octal` y `quad` (D-17).
9. ¿El registro manual de asistencia va en la API o fuera del sistema? (1.3) **Resuelta:** en la API (`POST /api/v1/asistencia`, RF-06 · C5), el Día 3 de B, con su botón en la pantalla Asistencia el Día 3 de C.
10. ¿Se agrega a R7 el paso 6? (3.7) **Resuelta:** sí. Desde la segunda muestra, cada una debe parecerse a la primera muestra aceptada de la inscripción; si no, `distinta_de_la_primera`.
11. ¿Alguien consigue una placa antes de la clase? (3.1) **Abierta:** se acordó compilar el diagnóstico con `CONFIG_SPIRAM_IGNORE_NOTFOUND=y`; falta decidir quién consigue la placa y cuál.

## Repositorio

- Repositorio privado en GitHub, con los tres como colaboradores.
- `main` no queda protegida: GitHub Free no protege ramas en repositorios privados. Por acuerdo del equipo, los cambios llegan a `main` solo por PR, nadie hace push directo y un PR se fusiona solo con las pruebas en verde (los workflows de GitHub Actions, RNF-06 · C3). GitHub no lo hace cumplir: es disciplina.
- Etiquetas: `frente-a`, `frente-b`, `frente-c` y `contrato`.

## Criterios de aceptación

- C1 Los contratos quedan aceptados; los cambios acordados quedan en el PR de `b/contratos-v1-1` (versión 1.1).
- C2 D-12 a D-19 quedan aceptadas o cambiadas en `specs/decisiones.md`.
- C3 Las preguntas abiertas (1 a 11) tienen respuesta y los archivos afectados están al día.
- C4 El repositorio privado existe, con los tres como colaboradores y las etiquetas, y la regla de PR con pruebas en verde queda escrita como acuerdo del equipo.
- C5 Hay una entrada en `docs/bitacora.md`.
