<!--
Nombre: README.md
Descripción: Simulador de la cámara de AccesIA con la webcam o con una carpeta de fotos (frente A): instalación, comandos, respuestas esperadas y pruebas.
Fecha de creación: 2026-11-11
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.1
-->

# Simulador · frente A

Hace lo mismo que la cámara, con la webcam del portátil o con una carpeta de fotos:

1. Detecta las caras con YuNet.
2. Elige la cara de mayor área y la recorta con la fórmula del contrato.
3. Envía el recorte al servidor y espera lo que dice el contrato antes de enviar otro.

Sirve para desarrollar sin hardware y es el plan C de la demo (D-10). Mientras llega el módulo de cámara, el simulador es la cámara del proyecto. La puerta por MQTT llega el Día 3.

- Specs: `specs/arquitectura.md` (Simulador) y los contratos `api-dispositivo.md`, `casos-recorte.json` y, el Día 3, `mqtt.md`.
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
uv run simulador webcam --codigo entrada [--como-camara] [--camara 0]
uv run simulador carpeta datos/prueba --codigo entrada [--como-camara]
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
| 2 | No se pudo probar: falta el token, la carpeta no tiene fotos, `esperado.json` está mal escrito, o el servidor respondió 401 o 403 |

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

Las pruebas no usan fotos de caras: usan imágenes sintéticas y un detector falso. En GitHub Actions corren con `.github/workflows/simulador.yml`, con el modelo en caché.
