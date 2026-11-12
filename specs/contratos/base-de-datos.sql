-- Nombre: base-de-datos.sql
-- Descripción: Esquema de PostgreSQL 18 + pgvector de AccesIA. Contrato del frente B.
-- Fecha de creación: 2026-11-11
-- Actualización: 2026-11-11
-- Autor: Equipo AccesIA
-- Versión: 1.2
--
-- La primera migración del servidor crea exactamente este esquema.
-- Requiere PostgreSQL 18 (uuidv7) y las extensiones vector (pgvector) y unaccent.
-- Explicación en specs/modelo-datos.md. Reglas en specs/reglas.md.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Administradores de la web. La clave se guarda con Argon2id.
CREATE TABLE administrador (
    id          uuid PRIMARY KEY DEFAULT uuidv7(),
    correo      text NOT NULL UNIQUE,
    clave_hash  text NOT NULL,
    nombre      text NOT NULL,
    activo      boolean NOT NULL DEFAULT true,
    creado      timestamptz NOT NULL DEFAULT now()
);

-- Horarios de entrada (R5, D-20). Cada horario tiene bloques, uno por día como máximo.
CREATE TABLE horario (
    id      uuid PRIMARY KEY DEFAULT uuidv7(),
    nombre  text NOT NULL UNIQUE,
    creado  timestamptz NOT NULL DEFAULT now()
);

-- Un bloque por horario y día. dia: 1 = lunes ... 7 = domingo (isodow). Se borra con su horario.
-- Que cada horario tenga al menos un bloque lo valida la API.
CREATE TABLE horario_bloque (
    horario_id      uuid NOT NULL REFERENCES horario (id) ON DELETE CASCADE,
    dia             smallint NOT NULL CHECK (dia BETWEEN 1 AND 7),
    hora_inicio     time NOT NULL,
    tolerancia_min  integer NOT NULL DEFAULT 10 CHECK (tolerancia_min BETWEEN 0 AND 120),
    PRIMARY KEY (horario_id, dia)
);

-- Quién puede entrar.
CREATE TABLE persona (
    id           uuid PRIMARY KEY DEFAULT uuidv7(),
    documento    text NOT NULL UNIQUE CHECK (documento ~ '^[0-9A-Za-z-]{3,20}$'),
    nombre       text NOT NULL CHECK (length(btrim(nombre)) BETWEEN 2 AND 120),
    rol          text NOT NULL DEFAULT 'estudiante'
                 CHECK (rol IN ('estudiante', 'docente', 'administrativo', 'otro')),
    horario_id   uuid REFERENCES horario (id) ON DELETE RESTRICT,
    activa       boolean NOT NULL DEFAULT true,
    creada       timestamptz NOT NULL DEFAULT now(),
    actualizada  timestamptz NOT NULL DEFAULT now()
);

-- Prueba de la autorización (Ley 1581). Solo un consentimiento vigente por persona.
CREATE TABLE consentimiento (
    id              uuid PRIMARY KEY DEFAULT uuidv7(),
    persona_id      uuid NOT NULL REFERENCES persona (id) ON DELETE CASCADE,
    version_texto   text NOT NULL,
    medio           text NOT NULL DEFAULT 'web' CHECK (medio IN ('web', 'papel')),
    registrado_por  uuid REFERENCES administrador (id) ON DELETE SET NULL,
    aceptado_en     timestamptz NOT NULL DEFAULT now(),
    revocado_en     timestamptz,
    CHECK (revocado_en IS NULL OR revocado_en >= aceptado_en)
);
CREATE UNIQUE INDEX consentimiento_vigente_unico ON consentimiento (persona_id) WHERE revocado_en IS NULL;

-- Cada cámara. token_hash: SHA-256 en hexadecimal del token (aleatorio de 32 bytes).
-- El código "servidor" está reservado: es el de los temas MQTT del servidor (mqtt.md).
CREATE TABLE dispositivo (
    codigo           text PRIMARY KEY CHECK (codigo ~ '^[a-z0-9-]{3,32}$' AND codigo <> 'servidor'),
    nombre           text NOT NULL,
    tipo             text NOT NULL DEFAULT 'tinyml' CHECK (tipo IN ('tinyml', 'respaldo', 'simulador')),
    token_hash       text NOT NULL,
    url_captura      text,
    activo           boolean NOT NULL DEFAULT true,
    ultimo_contacto  timestamptz,
    creado           timestamptz NOT NULL DEFAULT now(),
    CHECK (tipo <> 'respaldo' OR url_captura IS NOT NULL)
);

-- Cada sesión de inscripción (R9). Solo una activa por cámara.
CREATE TABLE inscripcion (
    id                  uuid PRIMARY KEY DEFAULT uuidv7(),
    persona_id          uuid NOT NULL REFERENCES persona (id) ON DELETE CASCADE,
    dispositivo_codigo  text NOT NULL REFERENCES dispositivo (codigo),
    estado              text NOT NULL DEFAULT 'activa'
                        CHECK (estado IN ('activa', 'completada', 'vencida', 'cancelada')),
    requeridas          smallint NOT NULL DEFAULT 5 CHECK (requeridas BETWEEN 1 AND 20),
    muestras            smallint NOT NULL DEFAULT 0,
    ultimo_motivo       text CHECK (ultimo_motivo IN
                        ('sin_cara', 'varias_caras', 'cara_pequena', 'borrosa', 'parece_otra_persona',
                         'distinta_de_la_primera')),
    creada              timestamptz NOT NULL DEFAULT now(),
    vence               timestamptz NOT NULL,
    terminada           timestamptz,
    CHECK (muestras BETWEEN 0 AND requeridas),
    CHECK ((estado = 'activa') = (terminada IS NULL))
);
CREATE UNIQUE INDEX inscripcion_activa_por_camara ON inscripcion (dispositivo_codigo) WHERE estado = 'activa';

-- Las huellas: 128 números normalizados de SFace. Nunca se guardan imágenes.
CREATE TABLE rostro (
    id              uuid PRIMARY KEY DEFAULT uuidv7(),
    persona_id      uuid NOT NULL REFERENCES persona (id) ON DELETE CASCADE,
    inscripcion_id  uuid REFERENCES inscripcion (id) ON DELETE SET NULL,
    huella          vector(128) NOT NULL,
    modelo          text NOT NULL DEFAULT 'sface_2021dec',
    fuente          text NOT NULL CHECK (fuente IN ('tinyml', 'respaldo', 'simulador')),
    calidad         real,  -- nitidez de R7 (varianza del laplaciano)
    creado          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX rostro_huella_hnsw ON rostro USING hnsw (huella vector_cosine_ops);
CREATE INDEX rostro_persona ON rostro (persona_id);

-- Cada intento de acceso. Las repeticiones de R4 y los recortes descartados no se guardan.
CREATE TABLE evento_acceso (
    id                  uuid PRIMARY KEY DEFAULT uuidv7(),
    fecha_hora          timestamptz NOT NULL DEFAULT now(),
    dispositivo_codigo  text NOT NULL REFERENCES dispositivo (codigo),
    persona_id          uuid REFERENCES persona (id) ON DELETE SET NULL,
    resultado           text NOT NULL CHECK (resultado IN ('permitido', 'denegado', 'desconocido')),
    motivo              text,
    similitud           real CHECK (similitud BETWEEN -1 AND 1),
    CHECK (
        (resultado = 'permitido' AND motivo IS NULL)
        OR (resultado = 'denegado' AND motivo IN ('inactiva', 'sin_consentimiento'))
        OR (resultado = 'desconocido' AND motivo = 'bajo_umbral')
    )
);
CREATE INDEX evento_fecha ON evento_acceso (fecha_hora DESC);
CREATE INDEX evento_persona_fecha ON evento_acceso (persona_id, fecha_hora DESC);
CREATE INDEX evento_dispositivo_fecha ON evento_acceso (dispositivo_codigo, fecha_hora DESC);

-- Una llegada por persona y día (R5). fecha es la fecha local de America/Bogota (R8).
-- origen: 'camara' la crea el primer evento permitido del día; 'manual' la registra
-- un administrador (RF-06 · C5), sin evento. salida es un extra del plan.
CREATE TABLE asistencia (
    id              uuid PRIMARY KEY DEFAULT uuidv7(),
    persona_id      uuid NOT NULL REFERENCES persona (id) ON DELETE CASCADE,
    fecha           date NOT NULL,
    llegada         timestamptz NOT NULL,
    salida          timestamptz,
    estado          text NOT NULL CHECK (estado IN ('a_tiempo', 'tarde', 'sin_horario')),
    minutos_tarde   integer CHECK (minutos_tarde >= 0),
    origen          text NOT NULL DEFAULT 'camara' CHECK (origen IN ('camara', 'manual')),
    evento_id       uuid REFERENCES evento_acceso (id) ON DELETE SET NULL,
    registrado_por  uuid REFERENCES administrador (id) ON DELETE SET NULL,
    UNIQUE (persona_id, fecha),
    CHECK ((estado = 'tarde') = (minutos_tarde IS NOT NULL)),
    CHECK (salida IS NULL OR salida >= llegada),
    CHECK (origen = 'camara' OR evento_id IS NULL),
    CHECK (origen = 'manual' OR registrado_por IS NULL)
);
CREATE INDEX asistencia_fecha ON asistencia (fecha);

-- Vistas del agente (D-15): sin documento, sin huellas y sin similitud.
CREATE VIEW v_persona_agente AS
SELECT p.nombre,
       p.rol,
       p.activa,
       h.nombre AS horario,
       (SELECT array_agg(b.dia ORDER BY b.dia)
        FROM horario_bloque b
        WHERE b.horario_id = h.id) AS dias_horario
FROM persona p
LEFT JOIN horario h ON h.id = p.horario_id;

CREATE VIEW v_asistencia_agente AS
SELECT a.fecha,
       p.nombre,
       a.llegada,
       a.estado,
       a.minutos_tarde
FROM asistencia a
JOIN persona p ON p.id = a.persona_id;

CREATE VIEW v_acceso_agente AS
SELECT e.fecha_hora,
       e.dispositivo_codigo AS camara,
       e.resultado,
       p.nombre
FROM evento_acceso e
LEFT JOIN persona p ON p.id = e.persona_id;

-- Rol de solo lectura del agente. El usuario "agente" (LOGIN, clave AGENTE_DB_PASSWORD)
-- lo crea la migración con: CREATE ROLE agente LOGIN PASSWORD '...' IN ROLE accesia_agente;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'accesia_agente') THEN
        CREATE ROLE accesia_agente NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO accesia_agente;
GRANT SELECT ON v_persona_agente, v_asistencia_agente, v_acceso_agente TO accesia_agente;

-- Datos iniciales: el horario de ejemplo de R5, con un bloque de lunes a viernes a las 07:00
-- y 10 min de tolerancia (se ajusta a la hora real de la clase).
WITH h AS (
    INSERT INTO horario (nombre) VALUES ('Clase IA') RETURNING id
)
INSERT INTO horario_bloque (horario_id, dia, hora_inicio, tolerancia_min)
SELECT h.id, d, '07:00', 10
FROM h, generate_series(1, 5) AS d;
