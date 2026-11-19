<!--
Nombre: reglas.md
Descripción: Reglas de negocio R1 a R9 de AccesIA con sus casos de prueba.
Fecha de creación: 2026-11-11
Actualización: 2026-11-19
Autor: Equipo AccesIA
Versión: 1.4
-->

# Reglas de negocio

Las reglas viven en el servidor y se prueban primero (pruebas unitarias con pytest). Sus valores salen de `infra/.env` (D-14). Cada caso de prueba lleva su marca, por ejemplo `R5 · borde`.

| Regla | Qué dice | Variable | Valor inicial |
| --- | --- | --- | --- |
| R1 | Hay coincidencia si la similitud llega al umbral | `UMBRAL_SIMILITUD` | 0,363 (umbral de coseno de SFace en LFW) |
| R2 | Cuenta la muestra más parecida | — | — |
| R3 | Inactiva o sin consentimiento vigente: denegado | — | — |
| R4 | La misma persona, cámara y resultado cuenta una vez dentro de la ventana | `VENTANA_REPETIDO_S` | 60 s |
| R5 | La primera entrada permitida del día, o la llegada registrada a mano, es la llegada; tarde si pasa la hora de inicio del bloque de ese día más su tolerancia | bloques del horario de la persona (D-20) | 07:00 + 10 min, de lunes a viernes (ejemplo) |
| R6 | Varios desconocidos seguidos generan una alerta | `ALERTA_DESCONOCIDOS`, `ALERTA_VENTANA_S` | 3 en 60 s |
| R7 | Calidad mínima de una muestra para inscribir, y tamaño mínimo para reconocer | `CARA_MIN_PX`, `NITIDEZ_MIN`, `UMBRAL_SIMILITUD` | 80 px (el servidor descarta por debajo de 64 px, o de 80 px con el cuadro completo), 60, 0,363 |
| R8 | Todo en hora de Colombia | `ZONA_HORARIA` | America/Bogota |
| R9 | Una inscripción pide 5 muestras, vence a los 120 s y hay una activa por cámara | `INSCRIPCION_MUESTRAS`, `INSCRIPCION_VENCE_S` | 5, 120 s |

## R1 · Umbral de similitud

- Similitud = 1 − distancia de coseno de pgvector: `1 - (huella <=> :v)`.
- Hay coincidencia si la similitud es mayor o igual que `UMBRAL_SIMILITUD`.
- La comparación tolera 1e-6: pgvector calcula en float32, y una similitud de 0,363 puede salir 0,36299998. La misma tolerancia vale en los pasos 5 y 6 de R7, que también comparan con el umbral.
- Sin coincidencia, el resultado es `desconocido` con motivo `bajo_umbral` y sin persona.
- El valor inicial viene de LFW, con caras de buena calidad. Se calibra con recortes como los de la cámara real: los del ESP32-S3 o los del simulador en modo «como la cámara» (RNF-07).

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R1 · igual al umbral | Mejor similitud 0,363, también 0,363 menos un paso de float32 (0,36299998) | Coincide |
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
- Revocar el consentimiento borra las huellas (RF-02 · C5), así que en la práctica quien revoca sale `desconocido`. `sin_consentimiento` queda como defensa por si la base llega a tener huellas sin consentimiento vigente; su prueba arma ese estado directamente en la base.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R3 · inactiva | Elena, inactiva, similitud 0,70 | `denegado`, `inactiva` |
| R3 · sin consentimiento | Bruno, activo, con huellas y sin consentimiento vigente (estado armado en la base) | `denegado`, `sin_consentimiento` |
| R3 · las dos | Inactiva y sin consentimiento | `denegado`, `inactiva` |
| R3 · todo bien | Activa y con consentimiento | `permitido` |
| R3 · revocado de punta a punta | Bruno revoca su consentimiento por la API (se borran sus huellas) y vuelve a la cámara; nadie más se le parece | `desconocido`, `bajo_umbral` |

## R4 · Ventana de repetición

- Si la misma persona, en la misma cámara y con el mismo resultado, tiene un evento guardado hace menos de `VENTANA_REPETIDO_S` segundos, la respuesta lleva `repetido: true` y el `evento_id` de ese evento.
- Una repetición no guarda evento y no cambia la asistencia.
- La repetición de un `permitido` publica el evento en MQTT con `repetido: true`, para que Home Assistant abra la puerta otra vez (`contratos/mqtt.md`). La repetición de un `denegado` no publica nada.
- La ventana se cuenta desde el último evento guardado. No aplica a los desconocidos.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R4 · dentro | Ana permitida en t = 0 s y otra vez en t = 30 s, misma cámara | Repetido, sin evento nuevo; publica el evento con `repetido: true` |
| R4 · denegado repetido | Elena denegada en t = 0 s y otra vez en t = 30 s, misma cámara | Repetido, sin evento nuevo y sin publicar |
| R4 · límite | Ana en t = 0 s y en t = 60 s | Evento nuevo |
| R4 · otra cámara | Ana en `entrada` (t = 0 s) y en `salida` (t = 30 s) | Evento nuevo |
| R4 · cambia el resultado | Elena denegada en t = 0 s, la activan y vuelve en t = 20 s | Evento nuevo, permitido |
| R4 · desconocidos | Dos desconocidos seguidos | Dos eventos (cuentan para R6) |

## R5 · Llegada y tardanza

- La primera entrada permitida del día (fecha local, R8) es la llegada.
- La llegada se califica con el bloque del horario de la persona para el día de la llegada: el día de la semana de la fecha local (R8), 1 = lunes … 7 = domingo (D-20).
- `sin_horario` si la persona no tiene horario o su horario no tiene bloque ese día.
- `a_tiempo` si la llegada es menor o igual que la hora de inicio del bloque más su tolerancia; `tarde` si es mayor. Se compara con segundos.
- `minutos_tarde` son los minutos completos entre la hora de inicio del bloque y la llegada; solo existe si es `tarde`.
- Ausentes del día: personas activas cuyo horario tiene bloque ese día y que no llegaron (RF-06 · C3).
- Un administrador puede registrar la llegada a mano (RF-06 · C5): se aplica esta misma regla a la hora que da, y la fecha es la fecha local de esa hora (R8). Si la persona ya tiene llegada ese día, la API responde 409 `asistencia_duplicada`.
- La primera llegada del día cuenta, venga de la cámara o sea manual: una entrada permitida posterior no la cambia.

Ejemplo: horario «Clase IA», con un bloque de lunes a viernes a las 07:00 y 10 min de tolerancia. Fechas del viernes 20 de noviembre de 2026.

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
| R5 · manual tarde | Llegada registrada a mano a las 07:25:30 | `tarde`, 25 minutos, origen `manual` |
| R5 · manual con llegada | Entra por la cámara a las 06:55 y después se registra a mano | 409 `asistencia_duplicada` |
| R5 · cámara después de manual | Llegada manual a las 07:05 y entrada permitida por la cámara a las 07:20 | La llegada sigue siendo la manual de las 07:05 |

Ejemplo con bloques distintos: horario «Lunes y miércoles», con un bloque el lunes a las 07:00 y 10 min de tolerancia, y otro el miércoles a las 18:00 y 15 min. Fechas de la semana del lunes 16 de noviembre de 2026.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R5 · bloque a tiempo | Llega el miércoles 18 a las 18:12 | `a_tiempo` (límite 18:15) |
| R5 · bloque tarde | Llega el miércoles 18 a las 18:20 | `tarde`, 20 minutos |
| R5 · día sin bloque | Llega el martes 17 a las 07:05 | `sin_horario` |

## R6 · Alerta de desconocidos

- Al guardar un desconocido, se cuentan los desconocidos de esa cámara guardados hace menos de `ALERTA_VENTANA_S` segundos (él incluido) que sean posteriores a su última alerta. Como en R4, uno de hace exactamente `ALERTA_VENTANA_S` segundos ya no cuenta.
- Si son `ALERTA_DESCONOCIDOS` o más, se publica `accesia/{codigo}/alerta`, salvo que la última alerta de esa cámara tenga menos de `ALERTA_VENTANA_S` segundos.
- La hora de la última alerta puede vivir en memoria: si el servidor se reinicia, se empieza de cero.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R6 · tres en la ventana | Desconocidos en t = 0, 20 y 50 s | Una alerta en t = 50 s |
| R6 · cuarto | Otro desconocido en t = 55 s | Sin alerta nueva |
| R6 · después de la espera | Desconocidos en t = 115, 120 y 125 s | Alerta nueva en t = 125 s |
| R6 · fuera de la ventana | Desconocidos en t = 0, 30 y 61 s | Sin alerta |
| R6 · borde | Desconocidos en t = 0, 30 y 60 s | Sin alerta (en t = 60 s, el de t = 0 ya no cuenta) |
| R6 · mezclados | Desconocido, desconocido y permitido | Sin alerta |
| R6 · dos cámaras | Dos en `entrada` y uno en `salida` | Sin alerta |

## R7 · Calidad de una muestra para inscribir

Se revisa en este orden y se responde el primer motivo que falle:

1. Hay al menos una cara con puntaje de YuNet ≥ 0,9; si no, `sin_cara`.
2. Hay exactamente una; si no, `varias_caras`.
3. La cara mide al menos 0,8 × `CARA_MIN_PX` de alto (64 px con el valor inicial); si no, `cara_pequena`. Con el cuadro completo (`api-dispositivo.md` 1.3), la mide el mismo YuNet del servidor, y el tope es `CARA_MIN_PX`, sin el 0,8. La cámara ya filtra con `CARA_MIN_PX` sobre la caja de ESP-DL; el margen cubre la diferencia con la caja de YuNet.
4. La nitidez (varianza del laplaciano de la cara alineada de 112 × 112 en gris) es al menos `NITIDEZ_MIN`; si no, `borrosa`.
5. No se parece (similitud ≥ `UMBRAL_SIMILITUD`) a otra persona ya inscrita: se busca la muestra más parecida entre las de otras personas (`WHERE persona_id <> :persona`); si llega al umbral, `parece_otra_persona`.
6. Desde la segunda muestra, se parece (similitud ≥ `UMBRAL_SIMILITUD`) a la primera muestra aceptada de esta misma inscripción; si no, `distinta_de_la_primera`. Así una cara que pasa por delante durante la inscripción no queda guardada como de la persona.

Al reconocer (sin inscripción activa) se usa la cara más grande (la de mayor área). Solo se descarta el recorte (`descartado`) si no hay cara (`sin_cara`) o si mide menos de 0,8 × `CARA_MIN_PX` de alto (`cara_pequena`). Con el cuadro completo (`api-dispositivo.md` 1.3), el tope es `CARA_MIN_PX`.

`NITIDEZ_MIN` se recalibra en clase con los valores de `calidad` de las muestras de la cámara real (D-14).

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R7 · válida | Una cara de 120 px, nitidez 150 | `muestra_aceptada` |
| R7 · sin cara | Foto de una pared | `muestra_rechazada`, `sin_cara` |
| R7 · dos caras | Dos personas en el recorte | `muestra_rechazada`, `varias_caras` |
| R7 · pequeña | Cara de 60 px (`CARA_MIN_PX` = 80) | `muestra_rechazada`, `cara_pequena` |
| R7 · tolerancia de tamaño | Cara de 70 px (`CARA_MIN_PX` = 80), nitidez 150 | `muestra_aceptada` (70 ≥ 64) |
| R7 · tolerancia de tamaño con un cuadro | La misma cara de 70 px, en un cuadro completo (`api-dispositivo.md` 1.3) | `muestra_rechazada`, `cara_pequena` (70 < 80) |
| R7 · borrosa | Nitidez 30 | `muestra_rechazada`, `borrosa` |
| R7 · otra persona | Al inscribir a Ana, la cara se parece a Bruno con 0,60 | `muestra_rechazada`, `parece_otra_persona` |
| R7 · se parece a las dos | Al inscribir a Ana, la cara da 0,80 con una muestra de Ana y 0,50 con una de Bruno | `muestra_rechazada`, `parece_otra_persona` |
| R7 · la misma persona | Se parece a las muestras de Ana | `muestra_aceptada` |
| R7 · primera muestra | Primera cara válida de la inscripción | `muestra_aceptada` (el paso 6 no aplica) |
| R7 · igual a la primera | Segunda muestra de Ana, similitud 0,65 con la primera aceptada | `muestra_aceptada` |
| R7 · distinta de la primera | Inscripción de Ana con una muestra aceptada; llega la cara de alguien no inscrito, con similitud 0,20 con esa muestra | `muestra_rechazada`, `distinta_de_la_primera` |
| R7 · reconocer con dos caras | Sin inscripción activa, dos caras | Se usa la más grande |
| R7 · reconocer pequeña | Sin inscripción activa, cara de 60 px | `descartado`, `cara_pequena` |
| R7 · reconocer con tolerancia | Sin inscripción activa, cara de 70 px | Se reconoce (no se descarta) |

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
- El vencimiento se revisa al llegar la siguiente cara de esa cámara, al consultar la inscripción, al abrir otra inscripción en esa cámara y al listar o ver las cámaras; no hace falta un proceso aparte.
- Si se revoca el consentimiento de la persona, su inscripción activa se cancela en la misma transacción en que se borran sus huellas (RF-02 · C5). Desactivar a la persona no cancela su inscripción.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| R9 · segunda en la misma cámara | Ya hay una activa en `entrada` | 409 `inscripcion_activa` |
| R9 · sin consentimiento | La persona no tiene consentimiento vigente | 422 `sin_consentimiento` |
| R9 · completa | Llegan 5 muestras aceptadas | `completada`; la siguiente cara se reconoce |
| R9 · vence | 2 aceptadas y pasan 121 s | `vencida`, quedan 2 muestras; la siguiente cara se reconoce |
| R9 · cancelar | La web la cancela | `cancelada` |
| R9 · otra cámara | Inscripción activa en `entrada` | `salida` sigue reconociendo |
| R9 · vencida sin revisar | La inscripción de `entrada` se abrió hace 130 s y no llegó ninguna cara ni consulta; se abre otra en `entrada` | La anterior queda `vencida` y la nueva se abre (201) |
| R9 · revoca a mitad | 2 aceptadas y se revoca el consentimiento | `cancelada`, sin huellas; la siguiente cara se reconoce |
| R9 · desactivar no cancela | 2 aceptadas y se desactiva a la persona | Sigue `activa` |
