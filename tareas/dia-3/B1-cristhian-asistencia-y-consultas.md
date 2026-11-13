<!--
Nombre: B1-cristhian-asistencia-y-consultas.md
Descripción: Tarea B1 del Día 3 del frente B: asistencia con R5 (desde la cámara y a mano) y la API de consulta (accesos, reporte del día, asistencia de una persona, huellas y configuración).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Frente B · B1 · Asistencia y API de consulta

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/asistencia`
- Depende de: B2 del Día 2, ya en `main`. Es la primera tarea del Día 3: B2 y B3 la necesitan.
- Lee primero: `CLAUDE.md`; `tareas/dia-3/00-todos-orden-e-hito-2.md`; `specs/reglas.md` (R4, R5 y R8); `specs/requisitos.md` (RF-05 · C3, RF-06, RF-12 · C1 y C3); `specs/contratos/openapi.yaml` (Accesos, Asistencia, Rostros y Configuración, con sus esquemas); `specs/modelo-datos.md` (`asistencia`); `specs/decisiones.md` (D-07, D-14 y D-20); `servidor/README.md`.

## Objetivo

La primera entrada permitida del día crea la llegada con R5, y un administrador puede registrarla a mano. La API da:

- el reporte del día;
- los accesos con filtros;
- la asistencia de una persona, sus huellas y la configuración.

Con esto C programa Accesos y Asistencia contra el servidor real, y B2 y B3 tienen la asistencia de la que dependen.

## Antes de empezar

Propón en el plan:

- Dónde vive R5:
  - una función pura con sus pruebas, que reciba la llegada y el bloque del día;
  - la usan la cámara, el registro manual y la semilla de B3.
- Cómo se crea la llegada desde la cámara:
  - en la misma transacción del evento `permitido`;
  - solo si la persona no tiene llegada ese día (`UNIQUE (persona_id, fecha)`);
  - las repeticiones de R4 no la crean, porque no guardan evento.
- Cómo deja el reconocimiento el dato de si este evento creó la llegada, para que B2 lo publique en el campo `asistencia` del Evento (`mqtt.md`).
- El rango por defecto de `verAsistenciaPersona` sin `desde` ni `hasta`, y el orden de los accesos dentro de una página.

## Hacer

1. R5 desde la cámara (RF-06 · C1 y C2):
   - La fecha es la fecha local de Colombia de la llegada (R8).
   - El bloque es el del horario de la persona para ese día de la semana, de 1 = lunes a 7 = domingo (D-20).
   - Califica así:
     - `a_tiempo` si la llegada es menor o igual que el inicio más la tolerancia, comparando con segundos;
     - si es mayor, `tarde`, con `minutos_tarde` en minutos completos desde el inicio del bloque;
     - `sin_horario` si la persona no tiene horario o su horario no tiene bloque ese día.
   - La llegada guarda `origen` `camara` y su `evento_id`. Una entrada permitida posterior no la cambia, tampoco si la primera fue manual.
2. `POST /api/v1/asistencia` (`registrarAsistenciaManual`, RF-06 · C5):
   - aplica R5 a la hora dada; la fecha es la fecha local de esa hora;
   - la llegada queda con `origen` `manual` y `registrado_por` igual al administrador de la sesión;
   - errores: 404 si la persona no existe; 422 `validacion` si la hora es futura; 409 `asistencia_duplicada` si ya tiene llegada ese día, también si dos registros llegan a la vez (la restricción `UNIQUE`, con su savepoint).
3. `GET /api/v1/asistencia` (`verAsistencia`, RF-06 · C3):
   - el reporte de una fecha, hoy por defecto, con `a_tiempo`, `tarde`, `sin_horario`, `ausentes` y `total_llegadas`;
   - ausentes son las personas activas cuyo horario tiene bloque ese día y no tienen llegada;
   - las llegadas manuales cuentan igual.
4. `GET /api/v1/personas/{persona_id}/asistencia` (`verAsistenciaPersona`, RF-12 · C3): las llegadas de la persona entre dos fechas, de la más reciente a la más antigua.
5. `GET /api/v1/accesos` (`listarAccesos`, RF-05 · C3):
   - filtros por fechas, resultado, persona y cámara;
   - paginación con `pagina` y `por_pagina` (20 por defecto, máximo 100), del más reciente al más antiguo;
   - un `desconocido` no lleva persona.
6. Huellas (RF-12 · C1):
   - `GET /api/v1/personas/{persona_id}/rostros` (`listarRostros`) devuelve las muestras sin las huellas;
   - `DELETE` en esa ruta (`borrarRostros`) y `DELETE /api/v1/rostros/{rostro_id}` (`borrarRostro`).
7. `GET /api/v1/configuracion` (`verConfiguracion`, D-14): los valores de las reglas que usa el servidor, los modelos de detección y de huella, y la versión.
8. Extra, si sobra tiempo: `GET /api/v1/asistencia.csv` (`exportarAsistencia`, RF-06 · C4).
9. Pruebas primero en las reglas, cada una con su marca:

   | Marca | Casos |
   | --- | --- |
   | `R5 · <caso>` | Los 15 de R5, también los manuales y los de bloques distintos, con el reloj de las pruebas (`reloj`) |
   | `RF-06 · C1`, `C2`, `C3` y `C5` | La llegada desde la cámara; las entradas siguientes; el reporte con ausentes; el registro manual con sus errores |
   | `RF-05 · C3` | Filtros y paginación de los accesos |
   | `RF-12 · C1` y `C3` | Borrar las huellas de una persona o una sola; la asistencia de una persona |
   | `R8 · fecha local` | Una llegada a las 23:30 de Colombia queda en ese día |
   | `contrato API · <operationId>` | Cada operación nueva con su esquema y los códigos de error del contrato |
   | `RNF-02 · C5` | Las rutas nuevas responden 401 sin sesión (la lista de `test_sesion.py`) |

10. `servidor/README.md`: rutas, decisiones y marcas nuevas.

## No hacer

- Nada de MQTT (B2) ni del servidor MCP (B3).
- No cambies los contratos. Si algo no encaja, propónlo en el PR.
- No toques `web/`, `simulador/`, `firmware/` ni `infra/`.
- No guardes imágenes.

## Criterios de aceptación

- C1 (R5; RF-06 · C1 y C2) La primera entrada permitida del día crea la llegada con su estado y sus minutos, y las siguientes no la cambian; los 15 casos de R5 pasan.
- C2 (RF-06 · C5) El registro manual aplica R5 y responde 409 `asistencia_duplicada` y 422 como dice el contrato.
- C3 (RF-06 · C3; RF-05 · C3) El reporte del día y los accesos con filtros cumplen sus esquemas.
- C4 (RF-12 · C1 y C3) Se borran las huellas de una persona y se ven sus llegadas.
- C5 (RNF-06 · C3) `uv run pytest` y `servidor.yml` en verde.
- C6 `servidor/README.md` y la bitácora al día.

## Al terminar

- Resume:
  - qué hiciste y qué pruebas corriste, con su resultado por marca;
  - qué decidiste donde el contrato no decía nada.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con todos los workflows del PR en verde. Cuando esté en `main`, avisa a C (Accesos y Asistencia contra el servidor real) y a quien siga con B2 y B3.
- El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
