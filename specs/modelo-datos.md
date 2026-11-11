<!--
Nombre: modelo-datos.md
Descripción: Tablas, relaciones, vistas del agente y usuarios de la base de datos de AccesIA.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.1
-->

# Modelo de datos

La fuente de verdad es `contratos/base-de-datos.sql`. Este archivo lo explica.

## Tablas

| Tabla | Para qué | Campos clave |
| --- | --- | --- |
| `administrador` | Entrar a la web | correo (único), clave con Argon2, nombre, activo |
| `horario` | Horas de entrada | nombre, hora de inicio, tolerancia en minutos, días (1 = lunes … 7 = domingo) |
| `persona` | Quién puede entrar | documento (único), nombre, rol, horario, activa |
| `consentimiento` | Prueba de la autorización (Ley 1581) | persona, versión del texto, medio, quién lo registró, aceptado en, revocado en. Solo uno vigente por persona |
| `dispositivo` | Cada cámara | código (clave; `servidor` está reservado), nombre, tipo (`tinyml`, `respaldo` o `simulador`), hash del token, URL de captura, activo, último contacto |
| `inscripcion` | Cada sesión de inscripción (R9) | persona, cámara, estado, muestras requeridas y aceptadas, motivo del último rechazo, vence. Solo una activa por cámara |
| `rostro` | Las huellas | persona, inscripción, huella `vector(128)`, modelo, fuente, calidad |
| `evento_acceso` | Cada intento | fecha y hora, cámara, persona (si coincide), resultado, motivo, similitud |
| `asistencia` | Una llegada por persona y día | persona, fecha local, llegada, salida (extra del plan), estado, minutos tarde, origen (`camara` o `manual`), evento (si vino de la cámara), quién la registró (si es manual) |

No hay tabla de imágenes: las fotos de caras nunca se guardan (RNF-01).

## Relaciones y borrado

- Una persona tiene un horario (o ninguno), varios consentimientos (uno vigente), varias inscripciones, varias huellas y una asistencia por día.
- Borrar una persona borra sus consentimientos, inscripciones, huellas y asistencia. Sus eventos quedan sin persona (RF-12).
- Revocar el consentimiento borra las huellas de la persona y cancela su inscripción activa, en la misma transacción (RF-02 · C5).
- Borrar un administrador deja sin autor los consentimientos y las llegadas manuales que registró.
- Un horario en uso no se puede borrar.
- Una cámara con eventos no se borra: se desactiva.

## La búsqueda central

```sql
SELECT r.persona_id, 1 - (r.huella <=> :v) AS similitud
FROM rostro r
ORDER BY r.huella <=> :v
LIMIT 1;
```

La huella se guarda normalizada. El índice HNSW (`vector_cosine_ops`) es aproximado, pero con pocas muestras da lo mismo que la búsqueda exacta; una prueba lo comprueba.

Al inscribir, el paso 5 de R7 hace la misma búsqueda solo entre las muestras de otras personas (`WHERE r.persona_id <> :persona`), y el paso 6 compara con la primera muestra aceptada de la inscripción (`WHERE r.inscripcion_id = :inscripcion`, la de `creado` más antiguo).

## Usuarios de la base

| Usuario | Rol | Qué puede hacer | Lo usa |
| --- | --- | --- | --- |
| `accesia` | Dueño | Todo sobre la base `accesia` | El servidor y sus migraciones |
| `agente` | `accesia_agente` | Solo `SELECT` sobre las tres vistas del agente | El servidor MCP (D-15) |

El rol `accesia_agente` lo crea el esquema. El usuario `agente`, con su clave de `AGENTE_DB_PASSWORD`, lo crea la migración.

## Vistas del agente

| Vista | Columnas | Qué deja fuera |
| --- | --- | --- |
| `v_persona_agente` | nombre, rol, activa, horario, días del horario | documento y huellas |
| `v_asistencia_agente` | fecha, nombre, llegada, estado, minutos tarde (también de las llegadas manuales) | documento, origen y quién registró la llegada |
| `v_acceso_agente` | fecha y hora, cámara, resultado, nombre | documento y similitud |

## Retención

Al terminar el semestre se borra la base completa (el volumen `datos-postgres`), como dice el texto del consentimiento.
