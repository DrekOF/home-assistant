<!--
Nombre: api-dispositivo.md
Descripción: Contrato entre la cámara (o el simulador) y el servidor de AccesIA.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Contrato cámara → servidor · versión 1.0

Lo cumplen el firmware y el simulador (frente A) y el servidor (frente B). En `openapi.yaml` es la operación `enviarRostro`.

## Petición

`POST /api/v1/dispositivos/{codigo}/rostros`

| Cabecera | Valor | Obligatoria |
| --- | --- | --- |
| `Authorization` | `Bearer <token de la cámara>` | Sí |
| `Content-Type` | `image/jpeg` | Sí |
| `X-AccesIA-Firmware` | Versión, por ejemplo `tinyml-esp32s3_eye-1.0.0` o `simulador-1.0.0` | No |
| `X-AccesIA-Puntaje` | Puntaje de la detección en la cámara, de 0 a 1 | No |

El cuerpo es el JPEG del recorte:

- La cara más grande del cuadro, con 25 % de margen por cada lado, ajustado a los bordes del cuadro.
- La cara mide al menos `CARA_MIN_PX` de alto; la cámara no envía caras más pequeñas.
- JPEG de calidad 80, de máximo 100 KB.

El servidor vuelve a detectar la cara con YuNet para alinearla antes de sacar la huella. Por eso el margen importa: sin él, YuNet puede no encontrar la cara.

## Respuesta 200

JSON con todos los campos siempre presentes (`null` cuando no aplica).

| Campo | Tipo | Qué es |
| --- | --- | --- |
| `modo` | `reconocer` o `inscribir` | Si la cámara tiene una inscripción activa (R9) |
| `resultado` | texto | Ver la tabla de resultados |
| `motivo` | texto o `null` | Ver la tabla de resultados |
| `persona` | `{id, nombre}` o `null` | Solo con `permitido`, `denegado` o en inscripción. Nunca con `desconocido` |
| `similitud` | número o `null` | Mejor similitud (R1). `null` si no hay muestras o en inscripción |
| `repetido` | booleano | `true` si es una repetición de R4 |
| `evento_id` | uuid o `null` | Evento guardado, o el original si es una repetición |
| `inscripcion` | objeto o `null` | `{id, muestras, requeridas, estado, vence}` en modo inscribir |
| `mensaje` | texto | Frase corta para el monitor serial o una pantalla |
| `hora` | fecha y hora | Hora del servidor en ISO 8601 con zona (R8) |

### Resultados

| Modo | `resultado` | `motivo` | ¿Guarda evento? | ¿Publica en MQTT? |
| --- | --- | --- | --- | --- |
| reconocer | `permitido` | `null` | Sí | `evento` |
| reconocer | `denegado` | `inactiva` o `sin_consentimiento` | Sí | `evento` |
| reconocer | `desconocido` | `bajo_umbral` | Sí | `evento`, y `alerta` si se cumple R6 |
| reconocer | `descartado` | `sin_cara` o `cara_pequena` | No | No |
| inscribir | `muestra_aceptada` | `null` | No (guarda la muestra) | No |
| inscribir | `muestra_rechazada` | `sin_cara`, `varias_caras`, `cara_pequena`, `borrosa` o `parece_otra_persona` | No | No |

Una repetición de R4 devuelve el resultado del evento original con `repetido: true` y su `evento_id`; no guarda ni publica nada.

### Ejemplos

Acceso permitido:

```json
{
  "modo": "reconocer",
  "resultado": "permitido",
  "motivo": null,
  "persona": { "id": "01a1e5c2-7f3a-7b2c-9d4e-5f6a7b8c9d0e", "nombre": "Ana Gómez" },
  "similitud": 0.71,
  "repetido": false,
  "evento_id": "01a1e6d0-1c2b-7e3f-8a9b-0c1d2e3f4a5b",
  "inscripcion": null,
  "mensaje": "Bienvenida, Ana",
  "hora": "2026-11-20T06:58:12-05:00"
}
```

Desconocido (no dice a quién se parece):

```json
{
  "modo": "reconocer",
  "resultado": "desconocido",
  "motivo": "bajo_umbral",
  "persona": null,
  "similitud": 0.21,
  "repetido": false,
  "evento_id": "01a1e6d4-9a8b-7c6d-8e5f-4a3b2c1d0e9f",
  "inscripcion": null,
  "mensaje": "No te reconozco",
  "hora": "2026-11-20T08:15:02-05:00"
}
```

Muestra aceptada durante una inscripción:

```json
{
  "modo": "inscribir",
  "resultado": "muestra_aceptada",
  "motivo": null,
  "persona": { "id": "01a1e5c2-7f3a-7b2c-9d4e-5f6a7b8c9d0e", "nombre": "Ana Gómez" },
  "similitud": null,
  "repetido": false,
  "evento_id": null,
  "inscripcion": {
    "id": "01a1e5d1-2b3c-7d4e-9f5a-6b7c8d9e0f1a",
    "muestras": 3,
    "requeridas": 5,
    "estado": "activa",
    "vence": "2026-11-19T16:02:00-05:00"
  },
  "mensaje": "Muestra 3 de 5",
  "hora": "2026-11-19T16:00:41-05:00"
}
```

## Errores

Cuerpo: `{"detalle": "texto para personas", "codigo": "texto para programas"}`.

| HTTP | `codigo` | Cuándo |
| --- | --- | --- |
| 401 | `token_invalido` | Falta el token, no corresponde o no existe una cámara con ese código (no se dice cuál de las tres) |
| 403 | `dispositivo_inactivo` | El token es válido pero la cámara está desactivada |
| 413 | `imagen_grande` | El cuerpo pasa de 100 KB |
| 415 | `tipo_no_soportado` | `Content-Type` no es `image/jpeg` |
| 422 | `imagen_invalida` | El JPEG no se puede leer |
| 429 | `demasiadas_peticiones` | Más de un recorte por segundo de esa cámara. Lleva la cabecera `Retry-After: 1` |

## Efectos en el servidor

- Cada petición con token válido actualiza `dispositivo.ultimo_contacto`.
- La imagen se procesa en memoria y se descarta. No se escribe en disco ni aparece en los registros (RNF-01).

## Qué hace la cámara con la respuesta

| Respuesta | Qué hace la cámara |
| --- | --- |
| `permitido`, `denegado` o `desconocido` | Muestra el mensaje y espera 3 s antes de enviar otro recorte |
| `descartado`, `muestra_aceptada` o `muestra_rechazada` | Sigue enviando, como máximo uno por segundo |
| 401 o 403 | Muestra el error y reintenta cada 30 s (el token se corrige por consola) |
| 429 | Espera lo que diga `Retry-After` |
| Sin respuesta en 5 s, o error 5xx | Reintenta con espera de 1, 2, 4 y hasta 10 s |

## Modo extraer (cámara de respaldo)

Para una cámara de tipo `respaldo`, el servidor pide `GET {url_captura}` cada segundo (tiempo de espera 3 s), detecta con YuNet en la imagen completa, recorta la cara más grande con el mismo margen y la procesa igual que una petición de este contrato. Esa cámara no tiene MQTT: la puerta queda solo como entidad de Home Assistant.

## Pruebas de contrato

- Las pruebas del servidor cubren cada fila de las tablas de resultados y de errores, con su marca, por ejemplo `contrato cámara · 429`.
- El simulador tiene un modo que envía las fotos de `datos/prueba/` y compara cada respuesta con la esperada.
- Prueba a mano desde PowerShell:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/dispositivos/entrada/rostros `
  -H "Authorization: Bearer $env:TOKEN_CAMARA" `
  -H "Content-Type: image/jpeg" `
  --data-binary "@datos/prueba/ana-1.jpg"
```
