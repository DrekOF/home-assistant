"""
Nombre: test_base_de_datos.py
Descripción: Pruebas del contrato de la base de datos: esquema, búsqueda vectorial, horarios por bloques (D-20) y permisos del agente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
"""

import math
import uuid
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

CONTRATO = Path(__file__).resolve().parents[2] / "specs" / "contratos" / "base-de-datos.sql"

# --- contrato BD · esquema ---

CATALOGO = {
    "columnas": """
        SELECT table_name, column_name, data_type, udt_name, is_nullable, coalesce(column_default, '')
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name <> 'alembic_version'""",
    "restricciones": """
        SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE connamespace = 'public'::regnamespace AND conrelid <> 0
          AND conrelid::regclass::text <> 'alembic_version'""",
    "índices": """
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename <> 'alembic_version'""",
    "vistas": "SELECT viewname, definition FROM pg_views WHERE schemaname = 'public'",
    "extensiones": "SELECT extname FROM pg_extension",
    "permisos del agente": """
        SELECT table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE grantee = 'accesia_agente'""",
}


def foto_del_catalogo(conexion: Connection) -> dict[str, set[tuple]]:
    return {parte: {tuple(fila) for fila in conexion.execute(text(consulta))} for parte, consulta in CATALOGO.items()}


@pytest.mark.marca("contrato BD · esquema")
def test_el_esquema_migrado_es_el_del_contrato(motor: Engine, url_base: str) -> None:
    # Una base aparte con el SQL del contrato tal cual, para comparar.
    with motor.connect().execution_options(isolation_level="AUTOCOMMIT") as administracion:
        administracion.exec_driver_sql("DROP DATABASE IF EXISTS contrato")
        administracion.exec_driver_sql("CREATE DATABASE contrato")
    motor_contrato = create_engine(make_url(url_base).set(database="contrato"))
    try:
        with motor_contrato.begin() as conexion:
            with conexion.connection.driver_connection.cursor() as cursor:
                cursor.execute(CONTRATO.read_text(encoding="utf-8"))
        with motor_contrato.connect() as conexion:
            esperado = foto_del_catalogo(conexion)
    finally:
        motor_contrato.dispose()

    with motor.connect() as conexion:
        migrado = foto_del_catalogo(conexion)

    assert esperado["columnas"], "El contrato no creó tablas."
    for parte in CATALOGO:
        assert migrado[parte] == esperado[parte], f"La base migrada no coincide con el contrato en: {parte}"


# --- contrato BD · vector ---

BUSQUEDA_CENTRAL = """
    SELECT r.persona_id, 1 - (r.huella <=> CAST(:v AS vector)) AS similitud
    FROM rostro r
    ORDER BY r.huella <=> CAST(:v AS vector)
    LIMIT 1"""


def huella(valores: dict[int, float]) -> str:
    """Huella de 128 números normalizada, en el formato de pgvector."""
    vector = [0.0] * 128
    for posicion, valor in valores.items():
        vector[posicion] = valor
    norma = math.sqrt(sum(valor * valor for valor in vector))
    return "[" + ",".join(f"{valor / norma:.6f}" for valor in vector) + "]"


def crear_persona(conexion: Connection, nombre: str, horario: uuid.UUID | None = None) -> uuid.UUID:
    return conexion.execute(
        text("INSERT INTO persona (documento, nombre, horario_id) VALUES (:d, :n, :h) RETURNING id"),
        {"d": uuid.uuid4().hex[:12], "n": nombre, "h": horario},
    ).scalar_one()


@pytest.mark.marca("contrato BD · vector")
def test_la_busqueda_central_devuelve_la_muestra_mas_parecida(conexion: Connection) -> None:
    ana = crear_persona(conexion, "Ana Gómez")
    bruno = crear_persona(conexion, "Bruno Díaz")
    for persona, valores in ((ana, {0: 1.0}), (ana, {1: 1.0, 2: 0.1}), (bruno, {3: 1.0})):
        conexion.execute(
            text("INSERT INTO rostro (persona_id, huella, fuente) VALUES (:p, CAST(:h AS vector), 'simulador')"),
            {"p": persona, "h": huella(valores)},
        )

    fila = conexion.execute(text(BUSQUEDA_CENTRAL), {"v": huella({1: 1.0})}).one()

    # R2: cuenta la muestra más parecida, que es la segunda de Ana.
    assert fila.persona_id == ana
    assert fila.similitud == pytest.approx(1 / math.sqrt(1.01), abs=1e-4)


# --- contrato BD · horarios (D-20) ---

def crear_horario(conexion: Connection, nombre: str, bloques: list[tuple[int, str, int]]) -> uuid.UUID:
    horario = conexion.execute(
        text("INSERT INTO horario (nombre) VALUES (:n) RETURNING id"), {"n": nombre}
    ).scalar_one()
    for dia, hora, tolerancia in bloques:
        conexion.execute(
            text("INSERT INTO horario_bloque (horario_id, dia, hora_inicio, tolerancia_min) VALUES (:h, :d, :i, :t)"),
            {"h": horario, "d": dia, "i": hora, "t": tolerancia},
        )
    return horario


@pytest.mark.marca("contrato BD · horarios")
def test_clase_ia_tiene_cinco_bloques(conexion: Connection) -> None:
    filas = conexion.execute(
        text("""
            SELECT b.dia, to_char(b.hora_inicio, 'HH24:MI') AS hora, b.tolerancia_min
            FROM horario_bloque b JOIN horario h ON h.id = b.horario_id
            WHERE h.nombre = 'Clase IA'
            ORDER BY b.dia""")
    ).all()

    assert [tuple(fila) for fila in filas] == [(dia, "07:00", 10) for dia in range(1, 6)]


@pytest.mark.marca("contrato BD · horarios")
def test_un_solo_bloque_por_horario_y_dia(conexion: Connection) -> None:
    horario = crear_horario(conexion, "Lunes y miércoles", [(1, "07:00", 10), (3, "18:00", 15)])

    with pytest.raises(IntegrityError) as falla:
        with conexion.begin_nested():
            conexion.execute(
                text("INSERT INTO horario_bloque (horario_id, dia, hora_inicio) VALUES (:h, 3, '19:00')"),
                {"h": horario},
            )
    assert falla.value.orig.sqlstate == "23505"


@pytest.mark.marca("contrato BD · horarios")
def test_un_horario_en_uso_no_se_borra(conexion: Connection) -> None:
    horario = crear_horario(conexion, "En uso", [(1, "07:00", 10)])
    crear_persona(conexion, "Carla Ruiz", horario)

    with pytest.raises(IntegrityError) as falla:
        with conexion.begin_nested():
            conexion.execute(text("DELETE FROM horario WHERE id = :h"), {"h": horario})
    # restrict_violation: la API lo traduce a 409 horario_en_uso (Día 2).
    assert falla.value.orig.sqlstate == "23001"


@pytest.mark.marca("contrato BD · horarios")
def test_borrar_un_horario_borra_sus_bloques(conexion: Connection) -> None:
    horario = crear_horario(conexion, "Sin uso", [(6, "08:00", 10)])

    conexion.execute(text("DELETE FROM horario WHERE id = :h"), {"h": horario})

    bloques = conexion.execute(
        text("SELECT count(*) FROM horario_bloque WHERE horario_id = :h"), {"h": horario}
    ).scalar_one()
    assert bloques == 0


@pytest.mark.marca("contrato BD · horarios")
def test_la_vista_del_agente_saca_los_dias_de_los_bloques(conexion: Connection) -> None:
    horario = crear_horario(conexion, "Lunes y miércoles", [(1, "07:00", 10), (3, "18:00", 15)])
    crear_persona(conexion, "Bruno Díaz", horario)
    crear_persona(conexion, "David Peña")

    dias = dict(
        conexion.execute(
            text("SELECT nombre, dias_horario FROM v_persona_agente WHERE nombre IN ('Bruno Díaz', 'David Peña')")
        ).all()
    )

    assert dias == {"Bruno Díaz": [1, 3], "David Peña": None}


# --- RF-08 · C4: el agente solo lee sus vistas ---

VISTAS_DEL_AGENTE = ["v_persona_agente", "v_asistencia_agente", "v_acceso_agente"]
TABLAS_PROHIBIDAS = ["persona", "rostro", "horario_bloque"]


@pytest.mark.marca("RF-08 · C4")
@pytest.mark.parametrize("vista", VISTAS_DEL_AGENTE)
def test_el_agente_lee_sus_vistas(conexion_agente: Connection, vista: str) -> None:
    conexion_agente.execute(text(f"SELECT * FROM {vista} LIMIT 1")).all()


@pytest.mark.marca("RF-08 · C4")
@pytest.mark.parametrize("tabla", TABLAS_PROHIBIDAS)
def test_el_agente_no_lee_las_tablas(conexion_agente: Connection, tabla: str) -> None:
    with pytest.raises(DBAPIError) as falla:
        conexion_agente.execute(text(f"SELECT * FROM {tabla} LIMIT 1"))
    assert falla.value.orig.sqlstate == "42501"


@pytest.mark.marca("RF-08 · C4")
def test_el_agente_no_inserta(conexion_agente: Connection) -> None:
    with pytest.raises(DBAPIError) as falla:
        conexion_agente.execute(text("INSERT INTO persona (documento, nombre) VALUES ('9999', 'Intruso')"))
    assert falla.value.orig.sqlstate == "42501"
