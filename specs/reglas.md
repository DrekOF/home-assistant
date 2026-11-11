<!--
Nombre: reglas.md
Descripción: Reglas de negocio R1 a R9 de AccesIA con sus casos de prueba.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Reglas de negocio

Las reglas viven en el servidor y se prueban primero (pruebas unitarias con pytest). Sus valores salen de `infra/.env` (D-14). Cada caso de prueba lleva su marca, por ejemplo `R5 · borde`.

| Regla | Qué dice | Variable | Valor inicial |
| --- | --- | --- | --- |
| R1 | Hay coincidencia si la similitud llega al umbral | `UMBRAL_SIMILITUD` | 0,363 (umbral de coseno de SFace en LFW) |
| R2 | Cuenta la muestra más parecida | — | — |
| R3 | Inactiva o sin consentimiento vigente: denegado | — | — |
| R4 | La misma persona, cámara y resultado cuenta una vez dentro de la ventana | `VENTANA_REPETIDO_S` | 60 s |
| R5 | La primera entrada del día es la llegada; tarde si pasa la hora de inicio más la tolerancia | horario de la persona | 07:00 + 10 min (ejemplo) |
| R6 | Varios desconocidos seguidos generan una alerta | `ALERTA_DESCONOCIDOS`, `ALERTA_VENTANA_S` | 3 en 60 s |
| R7 | Calidad mínima de una muestra para inscribir | `CARA_MIN_PX`, `NITIDEZ_MIN` | 80 px, 60 |
| R8 | Todo en hora de Colombia | `ZONA_HORARIA` | America/Bogota |
| R9 | Una inscripción pide 5 muestras, vence a los 120 s y hay una activa por cámara | `INSCRIPCION_MUESTRAS`, `INSCRIPCION_VENCE_S` | 5, 120 s |

## R1 · Umbral de similitud

- Similitud = 1 − distancia de coseno de pgvector: `1 - (huella <=> :v)`.
- Hay coincidencia si la similitud es mayor o igual que `UMBRAL_SIMILITUD`.
- Sin coincidencia, el resultado es `desconocido` con motivo `bajo_umbral` y sin persona.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R1 · igual al umbral | Mejor similitud 0,363 | Coincide |
| R1 · bajo el umbral | Mejor similitud 0,362 | `desconocido`, `bajo_umbral`, persona nula |
| R1 · base vacía | No hay muestras | `desconocido`, similitud nula |

## R2 · La muestra más parecida

- Se compara contra todas las muestras de todas las personas y cuenta la de mayor similitud.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R2 · varias muestras | Ana tiene muestras con 0,30 y 0,50 | Ana con 0,50 |
| R2 · dos personas | Ana 0,45 y Bruno 0,48 | Bruno con 0,48 |

## R3 · Estado de la persona

- Si hay coincidencia pero la persona está inactiva: `denegado`, motivo `inactiva`.
- Si está activa pero sin consentimiento vigente: `denegado`, motivo `sin_consentimiento`.
- Si pasan las dos cosas, el motivo es `inactiva`.
- Solo es `permitido` si está activa y con consentimiento vigente.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R3 · inactiva | Elena, inactiva, similitud 0,70 | `denegado`, `inactiva` |
| R3 · sin consentimiento | Bruno, activo, consentimiento revocado | `denegado`, `sin_consentimiento` |
| R3 · las dos | Inactiva y sin consentimiento | `denegado`, `inactiva` |
| R3 · todo bien | Activa y con consentimiento | `permitido` |

## R4 · Ventana de repetición

- Si la misma persona, en la misma cámara y con el mismo resultado, tiene un evento guardado hace menos de `VENTANA_REPETIDO_S` segundos, la respuesta lleva `repetido: true` y el `evento_id` de ese evento.
- Una repetición no guarda evento, no publica en MQTT y no cambia la asistencia.
- La ventana se cuenta desde el último evento guardado. No aplica a los desconocidos.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R4 · dentro | Ana permitida en t = 0 s y otra vez en t = 30 s, misma cámara | Repetido, sin evento nuevo |
| R4 · límite | Ana en t = 0 s y en t = 60 s | Evento nuevo |
| R4 · otra cámara | Ana en `entrada` (t = 0 s) y en `salida` (t = 30 s) | Evento nuevo |
| R4 · cambia el resultado | Elena denegada en t = 0 s, la activan y vuelve en t = 20 s | Evento nuevo, permitido |
| R4 · desconocidos | Dos desconocidos seguidos | Dos eventos (cuentan para R6) |

## R5 · Llegada y tardanza

- La primera entrada permitida del día (fecha local, R8) es la llegada.
- `sin_horario` si la persona no tiene horario o su horario no incluye ese día (1 = lunes … 7 = domingo).
- `a_tiempo` si la llegada es menor o igual que la hora de inicio más la tolerancia; `tarde` si es mayor. Se compara con segundos.
- `minutos_tarde` son los minutos completos entre la hora de inicio y la llegada; solo existe si es `tarde`.

Ejemplo: horario «Clase IA», lunes a viernes, 07:00, tolerancia 10 min. Fechas del viernes 20 de noviembre de 2026.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R5 · temprano | Llega 06:55 | `a_tiempo` |
| R5 · borde | Llega 07:10:00 | `a_tiempo` |
| R5 · un segundo tarde | Llega 07:10:01 | `tarde`, 10 minutos |
| R5 · tarde | Llega 07:25:30 | `tarde`, 25 minutos |
| R5 · segunda entrada | Entra 06:55 y otra vez 09:00 | La llegada sigue siendo 06:55 |
| R5 · sábado | Entra el sábado 21 a las 08:00 | `sin_horario` |
| R5 · sin horario | David no tiene horario | `sin_horario` |
| R5 · denegado no cuenta | Denegado 06:50 y permitido 07:20 | Llegada 07:20, `tarde`, 20 minutos |
| R5 · cerca de medianoche | Evento `2026-11-20T23:30:00-05:00` | Asistencia del 20 (en UTC ya es el 21) |

## R6 · Alerta de desconocidos

- Al guardar un desconocido, se cuentan los desconocidos de esa cámara en los últimos `ALERTA_VENTANA_S` segundos que sean posteriores a su última alerta.
- Si son `ALERTA_DESCONOCIDOS` o más, se publica `accesia/{codigo}/alerta`, salvo que la última alerta de esa cámara tenga menos de `ALERTA_VENTANA_S` segundos.
- La hora de la última alerta puede vivir en memoria: si el servidor se reinicia, se empieza de cero.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R6 · tres en la ventana | Desconocidos en t = 0, 20 y 50 s | Una alerta en t = 50 s |
| R6 · cuarto | Otro desconocido en t = 55 s | Sin alerta nueva |
| R6 · después de la espera | Desconocidos en t = 115, 120 y 125 s | Alerta nueva en t = 125 s |
| R6 · fuera de la ventana | Desconocidos en t = 0, 30 y 61 s | Sin alerta |
| R6 · mezclados | Desconocido, desconocido y permitido | Sin alerta |
| R6 · dos cámaras | Dos en `entrada` y uno en `salida` | Sin alerta |

## R7 · Calidad de una muestra para inscribir

Se revisa en este orden y se responde el primer motivo que falle:

1. Hay al menos una cara con puntaje de YuNet ≥ 0,9; si no, `sin_cara`.
2. Hay exactamente una; si no, `varias_caras`.
3. La cara mide al menos `CARA_MIN_PX` de alto; si no, `cara_pequena`.
4. La nitidez (varianza del laplaciano de la cara alineada de 112 × 112 en gris) es al menos `NITIDEZ_MIN`; si no, `borrosa`.
5. No se parece (similitud ≥ `UMBRAL_SIMILITUD`) a otra persona ya inscrita; si no, `parece_otra_persona`.

Al reconocer (sin inscripción activa) se usa la cara más grande. Solo se descarta el recorte (`descartado`) si no hay cara (`sin_cara`) o si es pequeña (`cara_pequena`).

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R7 · válida | Una cara de 120 px, nitidez 150 | `muestra_aceptada` |
| R7 · sin cara | Foto de una pared | `muestra_rechazada`, `sin_cara` |
| R7 · dos caras | Dos personas en el recorte | `muestra_rechazada`, `varias_caras` |
| R7 · pequeña | Cara de 60 px | `muestra_rechazada`, `cara_pequena` |
| R7 · borrosa | Nitidez 30 | `muestra_rechazada`, `borrosa` |
| R7 · otra persona | Al inscribir a Ana, la cara se parece a Bruno con 0,60 | `muestra_rechazada`, `parece_otra_persona` |
| R7 · la misma persona | Se parece a las muestras de Ana | `muestra_aceptada` |
| R7 · reconocer con dos caras | Sin inscripción activa, dos caras | Se usa la más grande |

## R8 · Hora de Colombia

- La base guarda fechas y horas con zona (`timestamptz`). La fecha de la asistencia es la fecha local de `America/Bogota`.
- La API y MQTT usan ISO 8601 con zona: `2026-11-20T07:58:12-05:00`.
- La web muestra la hora de Colombia en formato `es-CO`.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R8 · formato | Evento a las 12:58:12 UTC del 20 | `2026-11-20T07:58:12-05:00` |
| R8 · fecha local | `2026-11-21T03:30:00Z` | Fecha local 2026-11-20 |

## R9 · Sesión de inscripción

- Se abre para una persona con consentimiento vigente y una cámara activa. Solo hay una inscripción activa por cámara.
- Mientras está activa, todo lo que llega de esa cámara es inscripción: no se reconoce y no se abre la puerta.
- Pide `INSCRIPCION_MUESTRAS` muestras aceptadas; al completarlas queda `completada`.
- Vence `INSCRIPCION_VENCE_S` segundos después de abrirse. Al vencer o cancelarse, la cámara vuelve a reconocer. Las muestras aceptadas se conservan.
- El vencimiento se revisa al llegar la siguiente cara o al consultar la inscripción; no hace falta un proceso aparte.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R9 · segunda en la misma cámara | Ya hay una activa en `entrada` | 409 `inscripcion_activa` |
| R9 · sin consentimiento | La persona no tiene consentimiento vigente | 422 `sin_consentimiento` |
| R9 · completa | Llegan 5 muestras aceptadas | `completada`; la siguiente cara se reconoce |
| R9 · vence | 2 aceptadas y pasan 121 s | `vencida`, quedan 2 muestras; la siguiente cara se reconoce |
| R9 · cancelar | La web la cancela | `cancelada` |
| R9 · otra cámara | Inscripción activa en `entrada` | `salida` sigue reconociendo |
