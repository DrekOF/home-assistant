<!--
Nombre: 00-todos-acordar-contratos.md
Descripción: Tarea del Día 1 para los tres integrantes: revisar y acordar los contratos y crear el repositorio.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 1 · Todos · Acordar los contratos

- Responsables: Julián, Cristhian y Jhon
- Duración: unos 45 minutos
- Rama: no hace falta; si cambia un contrato, el cambio va en la rama `todos/contratos-v1`

## Objetivo

Que los tres entiendan y acepten los contratos antes de programar. Desde ahí cada frente trabaja por su lado.

## Antes de la reunión: revisión con Claude Code

Uno de los tres le pide a Claude Code una revisión y la comparte con los demás:

```text
Lee CLAUDE.md, specs/README.md y todos los archivos de specs/ y specs/contratos/. No escribas código ni cambies archivos. Dime: 1) inconsistencias entre los contratos o con las specs, 2) huecos que impidan empezar las tareas del Día 1, 3) riesgos técnicos. Sé concreto: archivo, sección y propuesta.
```

## Pasos

1. (10 min) Leer `specs/README.md`, `specs/decisiones.md` (sobre todo D-12 a D-19, que son propuestas) y `specs/arquitectura.md`.
2. (20 min) Revisar cada contrato con quien lo usa:

   | Contrato | Lo revisan |
   | --- | --- |
   | `api-dispositivo.md` | A y B |
   | `openapi.yaml` | B y C |
   | `mqtt.md` | A, B y C |
   | `mcp-agente.md` | B y C |
   | `base-de-datos.sql` | B |

3. (10 min) Resolver las preguntas abiertas y anotar lo acordado.
4. (5 min) Crear el repositorio y protegerlo.

## Preguntas abiertas

1. Código y nombre de la cámara de la demo. Propuesta: `entrada`, «Entrada».
2. Hora real de la clase, para ajustar el horario de ejemplo (hoy: «Clase IA», lunes a viernes, 07:00, 10 minutos de tolerancia).
3. Correo de contacto del equipo para `specs/consentimiento.md`.
4. ¿Aceptan las decisiones D-12 a D-19?
5. ¿Se quedan las metas propuestas: tiempos de respuesta, 9 de 10 preguntas del agente y montaje en 45 minutos?

## Repositorio

- Repositorio privado en GitHub, con los tres como colaboradores.
- `main` protegida: cambios solo por PR y sin push directo.
- Etiquetas: `frente-a`, `frente-b`, `frente-c` y `contrato`.

## Criterios de aceptación

- C1 Los contratos quedan aceptados en versión 1.0, o sus cambios quedan hechos en un PR.
- C2 D-12 a D-19 quedan aceptadas o cambiadas en `specs/decisiones.md`.
- C3 Las cinco preguntas abiertas tienen respuesta y los archivos afectados están al día.
- C4 El repositorio existe con `main` protegida.
- C5 Hay una entrada en `docs/bitacora.md`.
