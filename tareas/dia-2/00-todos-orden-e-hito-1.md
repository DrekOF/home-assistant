<!--
Nombre: 00-todos-orden-e-hito-1.md
Descripción: Día 2 para los tres integrantes: orden recomendado entre las tareas A, B1, B2 y C, y guion del Hito 1.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 2 · Todos · Orden de las tareas e Hito 1

- Responsables: Julián, Cristhian y Jhon
- Rama: cada tarea tiene la suya. El resultado del Hito 1 va en la rama `b/hito-1`, solo con la bitácora y las specs que cambien.
- Lee primero: `specs/plan.md`, `tareas/README.md` y las cuatro tareas del Día 2.

## Objetivo

Que las cuatro tareas del Día 2 avancen sin bloquearse y que al final del día el simulador inscriba y reconozca a alguien de punta a punta (Hito 1). Si el hito no se cumple, se resuelve antes de empezar el Día 3 (`specs/plan.md`).

## Tareas del Día 2

| Archivo | Responsable | Rama | Necesita en `main` |
| --- | --- | --- | --- |
| [A-julian-simulador.md](A-julian-simulador.md) | Julián Andrés Silva Morales | `a/simulador` | Nada para empezar; B2 para probar contra el servidor real |
| [B1-cristhian-sesion-y-api.md](B1-cristhian-sesion-y-api.md) | Cristhian Eduardo Sánchez Mosquera | `b/sesion-y-api` | Nada |
| [B2-cristhian-reconocimiento-e-inscripcion.md](B2-cristhian-reconocimiento-e-inscripcion.md) | Cristhian Eduardo Sánchez Mosquera | `b/reconocimiento` | B1 |
| [C-jhon-inscripcion-y-camaras.md](C-jhon-inscripcion-y-camaras.md) | Jhon Jairo Perdomo Perdomo | `c/inscripcion-y-camaras` | Nada para empezar (simulacro); B1 para Personas y Cámaras reales; B2 para Inscripción real |

## Orden recomendado

1. A, B1 y C empiezan a la vez, cada una en su rama desde `main`. A prueba con un servidor falso y C con el simulacro de la web.
2. B1 se fusiona primero. Trae la sesión, el primer administrador, personas, consentimiento, horarios, cámaras, el comando `crear-camara` y el contrato de la API 1.3, con `metodo_no_permitido` y el campo `inscripcion_activa` de las cámaras.
3. Con B1 en `main`:
   - B2 sale de `main` actualizado.
   - C actualiza su rama, prueba Personas, consentimiento y Cámaras contra el servidor real, y programa lo que usa `inscripcion_activa`. `npm run tipos` no debe dejar cambios, porque B1 ya regeneró los tipos.
4. B2 se fusiona: reconocimiento, R1 a R4, R7 e inscripción.
5. Con B2 en `main`, A envía recortes al servidor real y C prueba Inscripción con una inscripción real.
6. Con A, B1 y B2 en `main` (C es deseable, no obligatoria), el Hito 1.

Si una misma persona hace varias tareas el mismo día, este orden evita bloqueos: B1, B2, A y C. Así cada tarea encuentra en `main` lo que necesita.

## Acuerdos para no pisarse

- Contrato: B1 sube `openapi.yaml` a 1.3, con `metodo_no_permitido` y `Dispositivo.inscripcion_activa`. A y C lo aprueban en el PR de B1, porque usan ese contrato. Nadie más cambia un contrato hoy sin proponerlo antes (`specs/contratos/README.md`).
- Modelo YuNet: A y B2 usan el mismo archivo, de la misma URL y con el mismo SHA-256. La primera tarea que lo descargue anota la URL y el hash en `specs/arquitectura.md` (Piezas, modelos de cara); la otra usa esos.
- Modelos y fotos fuera del repositorio:
  - Los ONNX no se suben: en el PC quedan en `datos/modelos/`, y la imagen del servidor los descarga al construir.
  - Las fotos de prueba de cada uno quedan en su `datos/prueba/`, con el permiso de quien aparece. Git y Docker ignoran `datos/`.
- La tarea A del Día 1 (firmware) sigue abierta: nadie más toca `firmware/`. El simulador no depende de ella.
- `web/src/api/esquema.d.ts` solo lo cambia `npm run tipos`. B1 lo regenera en su PR porque cambia el contrato; nadie lo edita a mano.

## Guion del Hito 1

Qué se demuestra: una persona del equipo da su consentimiento, el simulador la inscribe con 5 muestras y después la reconoce; alguien no inscrito sale desconocido; y al revocar el consentimiento, sus huellas desaparecen.

### Preparación

- `main` actualizado con A, B1 y B2 (y C, si ya está).
- Docker Desktop abierto, con `infra/.env` y las claves de MQTT creadas el Día 1.
- Quien se inscribe es un integrante del equipo, que acepta su propio consentimiento.
- Tres terminales de PowerShell en la raíz del repositorio: servidor, web y simulador.
- El simulador ya corrió una vez (`uv sync` y una prueba sin nadie al frente), para que el modelo esté descargado: la inscripción vence a los 120 s.

### Pasos

1. Levantar el servidor (terminal 1):

   ```powershell
   docker compose -f infra/compose.yaml up -d --build
   curl.exe http://localhost:8000/api/v1/salud
   ```

   Esperado: `base` en `ok`. `mqtt` sale `sin_conexion` y `estado` sale `degradado` hasta el Día 3.

2. Crear la cámara del simulador (RF-10 · C5, terminal 1):

   ```powershell
   docker compose -f infra/compose.yaml exec servidor accesia crear-camara entrada --nombre Entrada --tipo simulador
   ```

   El token sale una sola vez. Cópialo a la terminal del simulador (terminal 3):

   ```powershell
   $env:TOKEN_CAMARA = "<token>"
   ```

   Si `entrada` ya existe de otra prueba, cambia su token en la pantalla Cámaras (o con `POST /api/v1/dispositivos/entrada/token`).

3. Persona y consentimiento (terminal 2):

   ```powershell
   cd web
   npm run dev
   ```

   En `http://localhost:5173`, entra con `ADMIN_CORREO` y `ADMIN_CLAVE_INICIAL` de `infra/.env`. En Personas, crea a la persona, abre su ficha, registra su consentimiento (web, versión 1.0) y pulsa «Inscribir».

4. Abrir la inscripción: en la pantalla Inscripción, con la persona y la cámara `entrada`. Esperado: «Muestra 0 de 5» y el tiempo que falta (120 s).

   Si la pantalla Inscripción todavía no está en `main`, ábrela desde PowerShell (terminal 3), con el id de la persona que sale en la dirección de su ficha:

   ```powershell
   $base = "http://localhost:8000/api/v1"
   $json = "application/json; charset=utf-8"
   $credenciales = @{ correo = "<ADMIN_CORREO>"; clave = "<ADMIN_CLAVE_INICIAL>" } | ConvertTo-Json
   Invoke-RestMethod -Method Post -Uri "$base/sesion" -ContentType $json -Body $credenciales -SessionVariable sesion
   $pedido = @{ persona_id = "<id de la persona>"; dispositivo = "entrada" } | ConvertTo-Json
   $inscripcion = Invoke-RestMethod -Method Post -Uri "$base/inscripciones" -ContentType $json -Body $pedido -WebSession $sesion
   Invoke-RestMethod -Uri "$base/inscripciones/$($inscripcion.id)" -WebSession $sesion
   ```

   La última línea muestra el avance; repítela para verlo cambiar.

5. Inscribir con el simulador (terminal 3), antes de que pasen los 120 s:

   ```powershell
   cd simulador
   uv run simulador webcam --codigo entrada --como-camara
   ```

   La persona mira la webcam. Esperado: cada respuesta es `muestra_aceptada` o `muestra_rechazada` con su motivo; la web pasa de «Muestra 1 de 5» a «Muestra 5 de 5» y la inscripción queda `completada` (RF-03 · C2, C3 y C6).

6. Reconocer, con el mismo simulador abierto: la cámara ya volvió a reconocer.
   - Esperado: `permitido`, con el nombre y una similitud mayor o igual que el umbral (R1 a R3).
   - Si vuelve a mirar antes de 60 s: `permitido` con `repetido: true` y el mismo `evento_id`, sin evento nuevo (R4).
7. Desconocido: otro integrante, sin inscribir, mira la webcam. Esperado: `desconocido`, `bajo_umbral`, sin persona y sin decir a quién se parece (RNF-01 · C3).
8. Modo carpeta, si alguien ya tiene sus fotos y respuestas esperadas en `datos/prueba/`:

   ```powershell
   uv run simulador carpeta datos/prueba --codigo entrada --como-camara
   ```

   Esperado: el resumen sin diferencias y código de salida 0.

9. Comprobar en la base (terminal 1):

   ```powershell
   docker compose -f infra/compose.yaml exec postgres psql -U accesia -d accesia -c "SELECT p.nombre, count(r.id) AS muestras FROM persona p LEFT JOIN rostro r ON r.persona_id = p.id GROUP BY p.nombre"
   docker compose -f infra/compose.yaml exec postgres psql -U accesia -d accesia -c "SELECT fecha_hora, resultado, motivo, round(similitud::numeric, 3) AS similitud FROM evento_acceso ORDER BY fecha_hora DESC LIMIT 10"
   ```

   Esperado: 5 muestras de la persona; un `permitido` por cada minuto que estuvo frente a la cámara, no uno por recorte (R4); los `desconocido` del paso 7, que no se agrupan; y ningún evento por los descartados ni por la inscripción (RF-05 · C1 y C2).

10. Revocar: en la ficha, revoca el consentimiento y vuelve a la webcam. Esperado: la persona queda con 0 muestras y sale `desconocido` (RF-02 · C5, R3 · revocado de punta a punta).
11. Bajar todo con `docker compose -f infra/compose.yaml down` y anotar el resultado.

### Criterios del hito

- H1 (RF-10 · C5) La cámara `entrada` se crea con `crear-camara`, y el simulador se autentica con su token.
- H2 (RF-02 · C2 y C4) Sin consentimiento no se puede inscribir; con consentimiento, sí.
- H3 (RF-03 · C1 a C3 y C6; R7; R9) Con el simulador, la inscripción llega a 5 muestras y queda `completada`. El avance y el último motivo se ven en la web, o en la respuesta si la pantalla todavía no está.
- H4 (RF-04 · C1 a C3; R1 a R4) La persona inscrita sale `permitido`, y la repetición antes de 60 s sale con `repetido: true` y sin evento nuevo.
- H5 (RNF-01 · C3) Alguien no inscrito sale `desconocido`, sin persona.
- H6 (RF-02 · C5; R3) Después de revocar, la persona no tiene huellas y sale `desconocido`.
- H7 (RNF-01 · C1) Ni el simulador ni el servidor guardaron imágenes: `git status` no muestra fotos fuera de `datos/` y los registros del servidor (`docker compose -f infra/compose.yaml logs servidor`) no muestran imágenes ni base64.
- H8 El resultado queda en la bitácora.

### Si algo falla

| Síntoma | Dónde mirar |
| --- | --- |
| 401 `token_invalido` | `$env:TOKEN_CAMARA` en la misma terminal del simulador, y el código `entrada` |
| 429 seguidos | El simulador debe esperar 1 s desde cada respuesta, no desde cada envío |
| `descartado` con `sin_cara` una y otra vez | El recorte: la fórmula y el margen (`casos-recorte.json`), y la luz |
| `muestra_rechazada` con `borrosa` una y otra vez | `NITIDEZ_MIN` en `infra/.env` (D-14). Anota los valores de `calidad` que se ven: se recalibra el Día 4 |
| `distinta_de_la_primera` | La primera muestra salió mal o pasó otra persona: cancela y abre otra inscripción |
| Nunca sale `permitido`, o la similitud queda cerca del umbral | Inscribir y reconocer en el mismo modo (`--como-camara` en los dos); ver el riesgo 3.2 de la revisión |
| 409 `inscripcion_activa` | Ya hay una abierta en `entrada`. La pantalla Inscripción ofrece verla o cancelarla, y Cámaras la muestra. Sin la pantalla, su id está en `inscripcion_activa` de `GET /api/v1/dispositivos/entrada` |

Si un cambio de `infra/.env` hace falta para pasar el hito, se anota en la bitácora con el valor anterior y el nuevo.

## Fuera del Día 2

Estas partes del contrato no tienen tarea hoy. Se asignan al escribir las tareas del Día 3:

- `GET` y `DELETE /api/v1/personas/{persona_id}/rostros` y `DELETE /api/v1/rostros/{rostro_id}` (RF-12 · C1).
- `GET /api/v1/configuracion`.

## Al terminar

- Una entrada en `docs/bitacora.md`, «Día 2 · Hito 1», con quién estuvo, qué pasó en cada paso, el tiempo de respuesta, las similitudes de `permitido` y `desconocido`, los rechazos y sus motivos, y lo que falló.
- Si el hito cambió alguna spec o algún valor de `infra/.env.example`, se actualiza con su versión.
- PR desde `b/hito-1` con la bitácora y esos cambios. Lo que quede pendiente pasa a las tareas del Día 3.
