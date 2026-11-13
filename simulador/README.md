<!--
Nombre: README.md
Descripción: Simulador de la cámara de AccesIA con la webcam o con una carpeta de fotos (frente A): instalación, comandos, respuestas esperadas, la puerta por MQTT y pruebas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.2
-->

# Simulador · frente A

Hace lo mismo que la cámara, con la webcam del portátil o con una carpeta de fotos:

1. Detecta las caras con YuNet.
2. Elige la cara de mayor área y la recorta con la fórmula del contrato.
3. Envía el recorte al servidor y espera lo que dice el contrato antes de enviar otro.

Con `--puerta`, también hace la parte MQTT de la cámara: recibe `ABRIR` y `CERRAR` y publica la puerta, su estado y su disponibilidad (ver «Puerta por MQTT»).

Sirve para desarrollar sin hardware y es el plan C de la demo (D-10). Mientras llega el módulo de cámara, el simulador es la cámara del proyecto.

- Specs: `specs/arquitectura.md` (Simulador) y los contratos `api-dispositivo.md`, `casos-recorte.json` y `mqtt.md` (la puerta).
- Nunca guarda imágenes: ni cuadros, ni recortes, ni fotos para depurar (RNF-01 · C1). Las fotos de prueba del equipo viven solo en `datos/prueba/`, que Git ignora.

## Instalación

Necesita [uv](https://docs.astral.sh/uv/). Desde `simulador/`, en PowerShell:

```powershell
uv sync
uv run simulador modelo
```

- `uv run simulador modelo` descarga YuNet a `datos/modelos/`, en la raíz del repositorio, y comprueba su SHA-256. Los otros comandos también lo descargan solos la primera vez.
- El commit de `opencv/opencv_zoo` y el hash están en `specs/arquitectura.md` (Piezas). Son los mismos que usa el servidor.
- En clase no hay internet (RNF-04 · C3): corre `uv run simulador modelo` antes, o copia el modelo del kit a `datos/modelos/`.

## Token de la cámara

El simulador se autentica como la cámara `entrada`, de tipo `simulador`, con el token de la variable `TOKEN_CAMARA`:

```powershell
docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador
$env:TOKEN_CAMARA = "<el token que mostró el comando>"
```

- El token vive solo en la terminal: nunca va en un archivo ni en la salida del simulador.
- Si `entrada` ya existe, se cambia su token en la pantalla Cámaras o con `POST /api/v1/dispositivos/entrada/token`.

## Comandos

```powershell
uv run simulador webcam --codigo entrada [--como-camara] [--camara 0] [--puerta]
uv run simulador carpeta datos/prueba --codigo entrada [--como-camara] [--puerta]
uv run simulador modelo
```

| Opción | Por defecto | Qué hace |
| --- | --- | --- |
| `--codigo` | (obligatoria) | Código de la cámara en el servidor |
| `--servidor` | `http://localhost:8000` | Dirección del servidor |
| `--como-camara` | apagado | Antes de detectar, deja la imagen como la del ESP32-S3 (ver abajo) |
| `--cara-min` | `80` | No envía caras de menos píxeles de alto; igual que `CARA_MIN_PX` |
| `--puntaje-min` | `0.9` | Puntaje mínimo de YuNet, el del paso 1 de R7 |
| `--camara` | `0` | Número de la webcam (solo en `webcam`) |
| `--puerta` | apagado | También hace la puerta por MQTT. Sin ella no se conecta al broker |
| `--broker` | `mqtt://127.0.0.1:1883` | Broker de la puerta; en el hotspot, `mqtt://192.168.137.1:1883`. Solo con `--puerta` |
| `--puerta-segundos` | `3` | Segundos que la puerta queda abierta con `ABRIR`, de 1 a 60. Solo con `--puerta` |

### Modo webcam

- Abre una ventana con la imagen, la caja de la cara elegida y el último mensaje del servidor.
- La caja sale verde si la cara se puede enviar y naranja si no (por ejemplo, si es pequeña).
- Se cierra con `q`, con Esc o con la X de la ventana.
- En la consola sale una línea por respuesta, con la espera que sigue. Por ejemplo, durante una inscripción:

  ```text
  16:00:41 muestra_aceptada · motivo: — · persona: Ana Gómez · similitud: — · repetido: no · Muestra 3 de 5 (espera 1 s)
  ```

- En la ventana, los textos van sin tildes («Gomez») porque OpenCV solo dibuja ASCII. La consola sí lleva tildes.

### Modo carpeta

- Envía cada foto (`.jpg`, `.jpeg`, `.png`, `.bmp` o `.webp`) en orden por nombre, con las mismas esperas que la cámara. Numera con ceros (`ana-01`, `ana-02` … `ana-10`) para que el orden sea el que esperas.
- Cada foto se envía una sola vez.
- Una ruta relativa se busca desde la carpeta actual y, si no existe, desde la raíz del repositorio. Así `datos/prueba` funciona desde la raíz y desde `simulador/`.
- Si la carpeta trae `esperado.json`, compara cada respuesta y termina con un resumen.

| Código de salida | Cuándo |
| --- | --- |
| 0 | Todo coincide, o la carpeta no trae `esperado.json` |
| 1 | Alguna respuesta no coincide con la esperada |
| 2 | No se pudo probar: falta el token, la carpeta no tiene fotos, `esperado.json` está mal escrito, o el servidor respondió 401 o 403. Con `--puerta`, también si falta `MQTT_CAMARA_CLAVE` o el código no sirve de client id |

Con 401 o 403 se detiene: con el mismo token, las demás fotos recibirían lo mismo.

## Respuestas esperadas (`esperado.json`)

Va en la misma carpeta que las fotos. Un ejemplo inventado:

```json
{
  "fotos": {
    "ana-01.jpg": { "resultado": "permitido", "persona": "Ana Gómez" },
    "ana-02.jpg": { "resultado": "permitido", "repetido": true },
    "bruno-01.jpg": { "resultado": "desconocido", "motivo": "bajo_umbral", "persona": null },
    "pared.jpg": { "enviada": false }
  }
}
```

- Se comparan solo los campos que escribas: `resultado`, `motivo`, `persona` (por nombre, o `null`), `repetido` y `modo`. Un campo con otro nombre es un error, para que no pase desapercibido un error de escritura.
- `"enviada": false` dice que la foto no debe enviarse (sin cara o cara pequeña); `"enviada": true`, que debe enviarse, responda lo que responda.
- Las fotos que no están en la lista se envían y se muestran, pero no se comparan.
- Una foto de la lista que no está en la carpeta cuenta como diferencia.
- El resumen sale así:

  ```text
  Resumen: 4 fotos, 4 con respuesta esperada, 1 con diferencias.
    bruno-01.jpg: resultado: se esperaba "desconocido" y llegó "permitido"
  ```

## Esperas entre recortes

Se cuentan desde que llega la respuesta, no desde que se envió (`api-dispositivo.md`):

| Respuesta | Espera antes del siguiente recorte |
| --- | --- |
| `descartado`, `muestra_aceptada` o `muestra_rechazada` | 1 s |
| `permitido`, `denegado` o `desconocido` | 3 s |
| 401 o 403 | 30 s (el modo carpeta se detiene) |
| 429 | Lo que diga `Retry-After`, y nunca menos de 1 s |
| Sin respuesta en 5 s, o 5xx | 1, 2, 4, 8 y después 10 s cada vez, hasta que llegue otra respuesta |
| Otras (413, 415, 422…) | 1 s |

## Modo «como la cámara»

Con `--como-camara`, cada imagen pasa por tres pasos antes de detectar, para que los recortes se parezcan a los del ESP32-S3 (RNF-07):

1. Se recorta al centro al rectángulo 4:3 más grande. Una webcam de 1280 × 720 (16:9) pasa a 960 × 720, perdiendo 160 px de cada lado.
2. Se reduce a 320 × 240. Como ya es 4:3, la escala es la misma en los dos ejes y la cara no se deforma.
3. Pasa por JPEG de calidad 80, en memoria.

Una foto vertical pierde arriba y abajo: toma las fotos de prueba horizontales. Inscribe y reconoce en el mismo modo, como pide la guía del Hito 1 (`tareas/dia-2/00-todos-orden-e-hito-1.md`, «Si algo falla»).

Sin `--como-camara`, una foto de celular de alta resolución da recortes grandes. Si un recorte pasa de 100 000 bytes, el simulador no lo envía y lo dice en la consola, porque el contrato no lo permite (máximo 100 KB, leído de la forma más estricta).

## Puerta por MQTT (`--puerta`)

Con `--puerta`, el simulador también hace la parte MQTT de la cámara (`mqtt.md`), igual que la placa del PR #11. Está apagada por defecto: en la demo, la placa maneja la puerta de `entrada` y el simulador solo envía los recortes de `entrada` por HTTP.

### La clave del usuario `camara`

Se conecta con el usuario `camara`. Su clave sale de la variable `MQTT_CAMARA_CLAVE`, la misma de `infra/.env`, y nunca va en una opción, para que no quede en el historial de PowerShell.

En el portátil del compose, desde `simulador/`, se carga sin mostrarla:

```powershell
$env:MQTT_CAMARA_CLAVE = (Select-String -Path ..\infra\.env -Pattern '^MQTT_CAMARA_CLAVE=(.+)$').Matches[0].Groups[1].Value
```

En otro PC, se escribe sin que se vea:

```powershell
$env:MQTT_CAMARA_CLAVE = [System.Net.NetworkCredential]::new("", (Read-Host "Clave de camara" -AsSecureString)).Password
```

En los dos casos, la clave vive solo en esa terminal.

Ejemplos:

```powershell
uv run simulador webcam --codigo entrada --como-camara --puerta
uv run simulador carpeta datos/prueba --codigo entrada --puerta --broker mqtt://192.168.137.1:1883
```

### Qué publica y qué escucha

| Tema | Cuándo | Mensaje | QoS | Retenido |
| --- | --- | --- | --- | --- |
| `accesia/{codigo}/disponible` | Al conectarse, al salir y como último deseo | `online` / `offline` | 1 | Sí |
| `accesia/{codigo}/puerta/set` | Lo escucha | `ABRIR` o `CERRAR` | 1 | No |
| `accesia/{codigo}/puerta/estado` | Al conectarse y cada vez que cambia | `abierta` / `cerrada` | 1 | Sí |
| `accesia/{codigo}/estado` | Al conectarse y cada 60 s | EstadoCamara | 0 | Sí |

- El client id es el código y el usuario es `camara`: la ACL lo deja solo en los temas de su código. Por eso, con `--puerta` el código debe tener de 3 a 32 minúsculas, números o guiones, y no puede ser `servidor`.
- `ABRIR` abre la puerta los segundos de `--puerta-segundos` y publica `abierta`; al cumplirse, publica `cerrada`. `CERRAR` la cierra antes.
- Igual que la placa:
  - un `ABRIR` con la puerta abierta vuelve a contar los segundos y no publica `abierta` otra vez;
  - un `CERRAR` con la puerta cerrada no publica nada;
  - cualquier otro mensaje (`abrir`, `ABRIR ` con espacio…) se ignora.

  El simulador, además, lo dice en la consola.
- EstadoCamara lleva solo `firmware` (el mismo texto de `X-AccesIA-Firmware`), `ip` y `segundos_encendida`:

  ```json
  {"firmware":"simulador-0.2.0","ip":"127.0.0.1","segundos_encendida":12}
  ```

  `ip` es la de este lado de la conexión con el broker: `127.0.0.1` si el broker corre en el mismo portátil.
- Al salir (`q`, Esc, Ctrl+C o el fin del modo carpeta):
  - si la puerta quedó abierta, publica `cerrada`;
  - después publica `offline` y se desconecta.

  Si el simulador se corta de golpe, el broker publica el último deseo, `offline`.
- El modo carpeta se desconecta al terminar la última foto: un `ABRIR` que llegue después ya no lo recibe.
- La conexión corre en su propio hilo, así que los recortes nunca esperan al broker.
  - Sin broker, reintenta a los 1, 2, 4, 8 y después cada 10 s, y lo avisa una sola vez en la consola.
  - Si el broker rechaza la clave, lo dice y no reintenta: la puerta queda apagada y los recortes siguen.

### Cómo se ve

- En la webcam, mientras la puerta está abierta, sale una franja verde arriba de la ventana: «PUERTA ABIERTA (2 s)».
- En los dos modos sale una línea con la hora en la consola:

  ```text
  19:31:40 Puerta conectada al broker 127.0.0.1:1883 como entrada: escucha ABRIR y CERRAR en accesia/entrada/puerta/set
  19:31:41 PUERTA ABIERTA (3 s)
  19:31:44 Puerta cerrada
  ```

### Con la placa

Dos clientes con el mismo client id no pueden estar conectados a la vez (`mqtt.md`, Broker): el broker saca al que ya estaba.

- Sin `--puerta`, el simulador no se conecta al broker. Así corre en el Hito 2, mientras la placa tiene la puerta de `entrada`.
- Si alguien usa `--puerta` con el código de la placa:
  1. El broker saca a la placa.
  2. La placa se reconecta a los 5 s y entonces el broker saca al simulador.
  3. El simulador se entera por MQTT 5 (DISCONNECT 0x8E, «sesión tomada»). Avisa en la consola, no se reconecta y sigue enviando recortes.

  Así, la placa siempre se queda con la puerta.
- Cuando la placa toma el código, el broker publica el último deseo del simulador (`offline`) y enseguida el `online` de la placa. Lo que queda retenido es lo de la placa.

### Probar a mano con el compose

Con el compose arriba, desde la raíz y en dos terminales. Las claves se cargan de `infra/.env` sin mostrarlas:

```powershell
$servidor = (Select-String -Path infra\.env -Pattern '^MQTT_SERVIDOR_CLAVE=(.+)$').Matches[0].Groups[1].Value
docker compose -f infra/compose.yaml exec mosquitto mosquitto_sub -u servidor -P $servidor -t "accesia/entrada/#" -v
```

```powershell
$ha = (Select-String -Path infra\.env -Pattern '^MQTT_HA_CLAVE=(.+)$').Matches[0].Groups[1].Value
docker compose -f infra/compose.yaml exec mosquitto mosquitto_pub -u homeassistant -P $ha -t "accesia/entrada/puerta/set" -m ABRIR -q 1
```

`mosquitto_sub` muestra `abierta` y, a los 3 s, `cerrada`.

Lo que publica el simulador queda retenido en `entrada` hasta que la placa lo reemplaza al conectarse. Para borrarlo antes, se publica un mensaje vacío retenido en cada tema:

```powershell
foreach ($tema in "disponible", "estado", "puerta/estado") { docker compose -f infra/compose.yaml exec mosquitto mosquitto_pub -u servidor -P $servidor -r -n -t "accesia/entrada/$tema" }
```

## Cómo está hecho

Cada imagen pasa por cinco etapas:

```text
fuente (webcam | carpeta) → preparar (--como-camara) → detectar y recortar → enviar → esperar
```

| Etapa | Archivo |
| --- | --- |
| Fuente | `webcam.py` (ventana y envío en otro hilo) y `carpeta.py` (fotos en orden, `esperado.json`) |
| Preparar | `imagen.py`: «como la cámara» y JPEG, todo en memoria |
| Detectar y recortar | `recortador.py`, con `deteccion.py` (YuNet) y `recorte.py` (elección de la cara y fórmula, sin OpenCV) |
| Enviar | `envio.py`: `POST` con `Authorization`, `Content-Type`, `X-AccesIA-Firmware` y `X-AccesIA-Puntaje` |
| Esperar | `ritmo.py`: la tabla de esperas, con un reloj que las pruebas reemplazan |

«Detectar y recortar» es una pieza aparte, con un solo método (`procesar`). Si algún día el simulador tiene que imitar a una cámara que envía el cuadro completo, se cambia solo esa pieza: el envío y las esperas no se tocan.

La puerta va aparte de esas etapas:

- `puerta.py` tiene la lógica pura, como `PuertaLogica` de la placa, con el reloj aparte.
- `mqtt.py` tiene la conexión con paho-mqtt, que corre en su propio hilo, y otro hilo que cierra la puerta a tiempo.

La ventana de la webcam solo le pregunta si debe mostrar la franja.

## Pruebas

Desde `simulador/`:

```powershell
uv run pytest
```

Cada prueba lleva su marca y al final sale el resumen por marca:

| Marca | Qué comprueba |
| --- | --- |
| `contrato recorte · <caso>` | Los casos de `specs/contratos/casos-recorte.json`, leídos del archivo, los mismos que usa el firmware |
| `RF-01 · C6 · cara mínima` | No envía sin cara ni con caras de menos de `cara_min`, en los dos modos |
| `RF-01 · C6 · espera` | 1 s desde la respuesta y 3 s tras `permitido`, `denegado` o `desconocido`, con un reloj falso |
| `contrato cámara · cabeceras` | Las cuatro cabeceras, el token de `TOKEN_CAMARA` (que no aparece en la salida) y el JPEG de 100 000 bytes o menos |
| `contrato cámara · respuestas` | 401 y 403, 429 con `Retry-After`, y las esperas ante fallas (servidor falso con `httpx.MockTransport`) |
| `contrato cámara · modo carpeta` | `esperado.json`, el resumen y los códigos de salida |
| `RNF-07 · como la cámara` | 320 × 240 sin deformar las imágenes 16:9, JPEG 80, y que el detector recibe la imagen reducida en los dos modos |
| `RNF-01 · C1` | Ningún modo escribe imágenes: falla si se llama a `cv2.imwrite`, si se abre un archivo para escribir o si aparece una imagen |
| `RNF-04 · C3 · modelo` | El SHA-256 del modelo, sin red, y que la URL y el hash son los de `arquitectura.md` |
| `RF-01 · C6 · YuNet` | YuNet real (necesita el modelo) no encuentra caras donde no las hay |
| `RF-01 · C6 · fotos reales` | Con las fotos de `datos/prueba/`, cada recorte cumple el contrato. Sin la carpeta, se salta y dice por qué |
| `contrato MQTT · puerta` | `ABRIR` y `CERRAR` exactos, los segundos configurados, `ABRIR` con la puerta abierta, los mensajes que no son órdenes y la franja de la ventana |
| `contrato MQTT · disponible` | El último deseo, `online` al conectarse, `offline` al salir (antes, `cerrada` si la puerta quedó abierta) y la reconexión |
| `contrato MQTT · estado del simulador` | Solo `firmware`, `ip` y `segundos_encendida`, con QoS 0, retenido y cada 60 s |
| `contrato MQTT · broker` | Sin `--puerta` no se crea el cliente MQTT. Además: las opciones, el código y la clave; que sin broker los recortes siguen; y que con «sesión tomada» o con la clave rechazada no reintenta |

- Las pruebas no usan fotos de caras: usan imágenes sintéticas y un detector falso.
- Casi todas las de MQTT usan un cliente paho falso y un reloj falso.
- `test_mqtt_broker.py` levanta su propio Mosquitto en un contenedor, con la configuración y la ACL de `infra/mosquitto/`, como `test_mqtt_acl.py` del servidor. Necesita Docker Desktop abierto; sin Docker se salta, y en la CI falla.
- En GitHub Actions corren con `.github/workflows/simulador.yml`, con el modelo en caché y Mosquitto en un contenedor.
