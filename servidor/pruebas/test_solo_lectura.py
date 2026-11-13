"""
Nombre: test_solo_lectura.py
Descripción: Prueba «RF-08 · C4» del servidor MCP: cada herramienta corre en una transacción de solo lectura con statement_timeout de 3 s, el usuario agente no puede cambiar las tablas y el servidor no arranca con otro usuario de la base (D-15).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

test_base_de_datos.py ya prueba que el usuario agente lee sus tres vistas, no lee las tablas y no inserta.
"""

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from accesia import agente, servidor_mcp
from accesia.config import configuracion

pytestmark = pytest.mark.marca("RF-08 · C4")


def test_la_transaccion_de_una_herramienta_es_de_solo_lectura(motor: Engine) -> None:
    """Aunque se conectara con el dueño de la base, dentro de la transacción de una herramienta no se escribe."""
    with agente.transaccion_de_lectura(motor) as conexion:
        assert conexion.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        assert conexion.execute(text("SHOW statement_timeout")).scalar_one() == "3s"
        with pytest.raises(DBAPIError, match="read-only transaction"):
            conexion.execute(text("INSERT INTO horario (nombre) VALUES ('No debe quedar')"))

    with motor.connect() as conexion:
        assert conexion.execute(text("SELECT count(*) FROM horario WHERE nombre = 'No debe quedar'")).scalar_one() == 0


@pytest.mark.parametrize(
    "sentencia",
    [
        "UPDATE persona SET activa = false",
        "DELETE FROM evento_acceso",
        "UPDATE dispositivo SET activo = true",
        "INSERT INTO asistencia (persona_id, fecha, llegada, estado) "
        "VALUES (gen_random_uuid(), current_date, now(), 'a_tiempo')",
        "DELETE FROM rostro",
    ],
)
def test_el_usuario_agente_no_cambia_las_tablas(motor_agente: Engine, sentencia: str) -> None:
    with motor_agente.connect() as conexion, pytest.raises(ProgrammingError, match="permission denied"):
        conexion.execute(text(sentencia))


def test_una_consulta_de_mas_de_3_s_vuelve_como_error(motor_agente: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    """statement_timeout corta la consulta a los 3 s y la herramienta responde {"error": …}, sin excepción."""

    def lenta(conexion, horas: int) -> dict:
        conexion.execute(text("SELECT pg_sleep(4)"))
        return {"no": "llega"}

    monkeypatch.setattr(agente, "desconocidos_recientes", lenta)

    assert agente.Herramientas(motor_agente).desconocidos_recientes(24) == {
        "error": "La consulta tardó más de 3 s. Prueba con menos días."
    }


def test_sin_base_la_herramienta_responde_con_error() -> None:
    from sqlalchemy import create_engine

    sin_base = create_engine("postgresql+psycopg://agente:clave@127.0.0.1:1/accesia", connect_args={"connect_timeout": 1})

    assert agente.Herramientas(sin_base).buscar_persona("Ana") == {
        "error": "No se pudo consultar la base de AccesIA. Intenta de nuevo en un momento."
    }


def test_el_servidor_mcp_no_arranca_con_otro_usuario(monkeypatch: pytest.MonkeyPatch,
                                                     capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://accesia:clave@localhost:5434/accesia")
    configuracion.cache_clear()
    try:
        assert servidor_mcp.correr() == 1
    finally:
        monkeypatch.undo()
        configuracion.cache_clear()

    assert "usuario «agente»" in capsys.readouterr().err
