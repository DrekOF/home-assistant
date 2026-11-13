"""
Nombre: test_semilla.py
Descripción: Prueba «contrato agente · evaluación»: semilla agente crea la tabla de la evaluación de mcp-agente.md con fechas relativas a hoy, convive con datos reales sin tocarlos, se reemplaza, se borra sola y revisa las preguntas 1 a 9.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, time, timedelta

import armar
import pytest
from hora_fija import HOY, ahora_fijo
from sqlalchemy import Connection, text

from accesia import semilla
from accesia.comandos import principal

pytestmark = pytest.mark.marca("contrato agente · evaluación")

CLASE = "Clase todos los días"


@pytest.fixture(autouse=True)
def hoy() -> Iterator[datetime]:
    with ahora_fijo(HOY):
        yield HOY


def _filas(conexion: Connection, consulta: str, **parametros) -> list[tuple]:
    return [tuple(fila) for fila in conexion.execute(text(consulta), parametros)]


def _eventos(conexion: Connection) -> list[tuple]:
    """Los eventos de la semilla en hora de Colombia: (fecha y hora, nombre o None, resultado, motivo)."""
    return _filas(
        conexion,
        "SELECT to_char(e.fecha_hora AT TIME ZONE 'America/Bogota', 'YYYY-MM-DD HH24:MI:SS'), p.nombre, e.resultado, "
        "e.motivo FROM evento_acceso e LEFT JOIN persona p ON p.id = e.persona_id WHERE e.id = ANY(:ids) "
        "ORDER BY e.fecha_hora",
        ids=semilla.EVENTO_IDS,
    )


def _llegadas(conexion: Connection) -> list[tuple]:
    return _filas(
        conexion,
        "SELECT a.fecha::text, p.nombre, to_char(a.llegada AT TIME ZONE 'America/Bogota', 'HH24:MI'), a.estado, "
        "a.minutos_tarde, a.origen FROM asistencia a JOIN persona p ON p.id = a.persona_id "
        "WHERE p.id = ANY(:ids) ORDER BY a.fecha, a.llegada",
        ids=semilla.PERSONA_IDS,
    )


def test_crea_la_tabla_de_la_evaluacion(conexion: Connection) -> None:
    resultado = semilla.crear(conexion)

    assert _filas(
        conexion,
        "SELECT p.documento, p.nombre, p.rol, p.activa, h.nombre FROM persona p "
        "LEFT JOIN horario h ON h.id = p.horario_id WHERE p.id = ANY(:ids) ORDER BY p.documento",
        ids=semilla.PERSONA_IDS,
    ) == [
        ("SEMILLA-01", "Ana Gómez", "estudiante", True, CLASE),
        ("SEMILLA-02", "Bruno Díaz", "estudiante", True, CLASE),
        ("SEMILLA-03", "Carla Ruiz", "estudiante", True, CLASE),
        ("SEMILLA-04", "David Peña", "docente", True, None),
        ("SEMILLA-05", "Elena Mora", "estudiante", False, CLASE),
        ("SEMILLA-06", "Felipe Soto", "estudiante", True, CLASE),
    ]
    # Siete bloques, de lunes a domingo, a las 07:00 con 10 min de tolerancia.
    assert _filas(
        conexion,
        "SELECT dia, hora_inicio, tolerancia_min FROM horario_bloque WHERE horario_id = :id ORDER BY dia",
        id=semilla.HORARIO_ID,
    ) == [(dia, time(7, 0), 10) for dia in range(1, 8)]
    assert conexion.execute(
        text("SELECT count(*) FROM consentimiento WHERE persona_id = ANY(:ids) AND revocado_en IS NULL"),
        {"ids": semilla.PERSONA_IDS},
    ).scalar_one() == 6
    assert _eventos(conexion) == [
        ("2026-11-18 06:50:00", "Bruno Díaz", "permitido", None),
        ("2026-11-18 07:00:00", "Carla Ruiz", "permitido", None),
        ("2026-11-18 07:11:00", "Felipe Soto", "permitido", None),
        ("2026-11-18 07:20:00", "Ana Gómez", "permitido", None),
        ("2026-11-19 04:00:00", None, "desconocido", "bajo_umbral"),
        ("2026-11-19 06:58:00", "Ana Gómez", "permitido", None),
        ("2026-11-19 07:05:00", "Bruno Díaz", "permitido", None),
        ("2026-11-19 07:12:00", "Carla Ruiz", "permitido", None),
        ("2026-11-19 07:40:00", "David Peña", "permitido", None),
        ("2026-11-19 07:45:00", "Elena Mora", "denegado", "inactiva"),
        ("2026-11-19 09:30:00", "Ana Gómez", "permitido", None),
        ("2026-11-20 08:00:00", None, "desconocido", "bajo_umbral"),
        ("2026-11-20 08:00:20", None, "desconocido", "bajo_umbral"),
        ("2026-11-20 08:00:41", None, "desconocido", "bajo_umbral"),
    ]
    # Las llegadas, calificadas con R5: la segunda entrada de Ana ayer no es otra llegada.
    assert _llegadas(conexion) == [
        ("2026-11-18", "Bruno Díaz", "06:50", "a_tiempo", None, "camara"),
        ("2026-11-18", "Carla Ruiz", "07:00", "a_tiempo", None, "camara"),
        ("2026-11-18", "Felipe Soto", "07:11", "tarde", 11, "camara"),
        ("2026-11-18", "Ana Gómez", "07:20", "tarde", 20, "camara"),
        ("2026-11-19", "Ana Gómez", "06:58", "a_tiempo", None, "camara"),
        ("2026-11-19", "Bruno Díaz", "07:05", "a_tiempo", None, "camara"),
        ("2026-11-19", "Carla Ruiz", "07:12", "tarde", 12, "camara"),
        ("2026-11-19", "David Peña", "07:40", "sin_horario", None, "camara"),
    ]
    assert (resultado.personas, resultado.eventos, resultado.llegadas) == (6, 14, 8)
    assert resultado.hoy.isoformat() == "2026-11-20"
    assert all(revisada.coincide for revisada in resultado.revision)
    assert [revisada.pregunta.numero for revisada in resultado.revision] == list(range(1, 10))


def test_si_no_hay_camara_entrada_la_crea_sin_mostrar_su_token(conexion: Connection) -> None:
    resultado = semilla.crear(conexion)

    assert resultado.camara_creada
    nombre, tipo, token_hash = conexion.execute(
        text("SELECT nombre, tipo, token_hash FROM dispositivo WHERE codigo = 'entrada'")
    ).one()
    assert (nombre, tipo, len(token_hash)) == ("Entrada", "simulador", 64)
    assert any("la creé sin mostrar su token" in linea for linea in semilla.describir(resultado))


def test_si_hay_datos_reales_sin_la_opcion_no_escribe_nada(conexion: Connection) -> None:
    armar.persona(conexion, documento="1075999001", nombre="Persona Real")

    with pytest.raises(semilla.ErrorDeSemilla, match="--con-datos-reales") as error:
        semilla.crear(conexion)

    assert "1 persona y 0 eventos" in str(error.value)
    assert conexion.execute(text("SELECT count(*) FROM persona")).scalar_one() == 1
    assert conexion.execute(text("SELECT count(*) FROM horario WHERE nombre = :n"), {"n": CLASE}).scalar_one() == 0


def test_con_la_opcion_agrega_sus_datos_y_no_toca_los_reales(conexion: Connection) -> None:
    armar.camara(conexion, "entrada")
    real = armar.persona(conexion, documento="1075999001", nombre="Persona Real", horario_id=armar.clase_ia(conexion))
    armar.evento(conexion, "entrada", real, fecha_hora=HOY - timedelta(hours=1))
    antes = {
        "persona": _filas(conexion, "SELECT * FROM persona WHERE id = :id", id=real),
        "eventos": _filas(conexion, "SELECT * FROM evento_acceso WHERE persona_id = :id", id=real),
        "camara": _filas(conexion, "SELECT * FROM dispositivo WHERE codigo = 'entrada'"),
    }

    resultado = semilla.crear(conexion, con_datos_reales=True)

    assert resultado.ajenos == semilla.Ajenos(personas=1, eventos=1)
    assert not resultado.camara_creada
    assert antes == {
        "persona": _filas(conexion, "SELECT * FROM persona WHERE id = :id", id=real),
        "eventos": _filas(conexion, "SELECT * FROM evento_acceso WHERE persona_id = :id", id=real),
        "camara": _filas(conexion, "SELECT * FROM dispositivo WHERE codigo = 'entrada'"),
    }
    assert any("no los toqué" in linea for linea in semilla.describir(resultado))


def test_la_revision_dice_que_respuesta_cambia_con_datos_reales(conexion: Connection) -> None:
    """Una persona real con horario de lunes a viernes y sin llegada ayer (jueves) también faltó: cambia la 2."""
    armar.persona(conexion, documento="1075999002", nombre="Rosa Real", horario_id=armar.clase_ia(conexion))

    resultado = semilla.crear(conexion, con_datos_reales=True)

    distintas = [revisada for revisada in resultado.revision if not revisada.coincide]
    assert [revisada.pregunta.numero for revisada in distintas] == [2]
    assert distintas[0].obtenido == "Felipe Soto, Rosa Real"
    lineas = semilla.describir(resultado)
    assert "Preguntas 1 a 9 con las herramientas: 8 de 9 como dice el contrato." in lineas
    assert any(linea.startswith("  ✗ 2.") and "El contrato espera «Felipe Soto»" in linea for linea in lineas)


def test_repetirla_reemplaza_lo_suyo_con_las_fechas_del_dia(conexion: Connection) -> None:
    semilla.crear(conexion)

    with ahora_fijo(HOY + timedelta(days=1)):
        resultado = semilla.crear(conexion)

    assert (resultado.personas, resultado.eventos, resultado.llegadas) == (6, 14, 8)
    assert conexion.execute(text("SELECT count(*) FROM persona")).scalar_one() == 6
    assert conexion.execute(text("SELECT count(*) FROM evento_acceso")).scalar_one() == 14
    assert _eventos(conexion)[0] == ("2026-11-19 06:50:00", "Bruno Díaz", "permitido", None)  # antier, ahora el 19
    assert all(revisada.coincide for revisada in resultado.revision)


def test_borrar_quita_solo_lo_suyo(conexion: Connection) -> None:
    armar.camara(conexion, "entrada")
    real = armar.persona(conexion, documento="1075999001", nombre="Persona Real")
    evento_real = armar.evento(conexion, "entrada", real, fecha_hora=HOY - timedelta(hours=1))
    semilla.crear(conexion, con_datos_reales=True)

    borrado = semilla.borrar(conexion)

    assert borrado == semilla.Borrado(personas=6, eventos=14, horario=True)
    for tabla, columna, ids in (("persona", "id", semilla.PERSONA_IDS), ("evento_acceso", "id", semilla.EVENTO_IDS),
                                ("consentimiento", "persona_id", semilla.PERSONA_IDS),
                                ("asistencia", "persona_id", semilla.PERSONA_IDS)):
        assert conexion.execute(
            text(f"SELECT count(*) FROM {tabla} WHERE {columna} = ANY(:ids)"), {"ids": ids}
        ).scalar_one() == 0, tabla
    assert conexion.execute(text("SELECT count(*) FROM horario WHERE nombre = :n"), {"n": CLASE}).scalar_one() == 0
    assert conexion.execute(text("SELECT count(*) FROM persona WHERE id = :id"), {"id": real}).scalar_one() == 1
    assert conexion.execute(text("SELECT count(*) FROM evento_acceso WHERE id = :id"), {"id": evento_real}).scalar_one() == 1
    assert conexion.execute(text("SELECT count(*) FROM dispositivo WHERE codigo = 'entrada'")).scalar_one() == 1


def test_borrar_sin_semilla_no_borra_nada(conexion: Connection) -> None:
    armar.persona(conexion, documento="1075999001", nombre="Persona Real")

    assert semilla.borrar(conexion) == semilla.Borrado(personas=0, eventos=0, horario=False)
    assert conexion.execute(text("SELECT count(*) FROM persona")).scalar_one() == 1


def test_no_toca_un_horario_con_su_nombre_que_no_es_suyo(conexion: Connection) -> None:
    armar.horario(conexion, CLASE, (1, "08:00", 5))

    with pytest.raises(semilla.ErrorDeSemilla, match="no creó la semilla"):
        semilla.crear(conexion, con_datos_reales=True)

    assert _filas(conexion, "SELECT dia, hora_inicio FROM horario_bloque b JOIN horario h ON h.id = b.horario_id "
                            "WHERE h.nombre = :n", n=CLASE) == [(1, time(8, 0))]


def test_no_toca_una_persona_con_un_documento_de_la_semilla(conexion: Connection) -> None:
    armar.persona(conexion, documento="SEMILLA-01", nombre="Otra Persona")

    with pytest.raises(semilla.ErrorDeSemilla, match="SEMILLA-01"):
        semilla.crear(conexion, con_datos_reales=True)

    assert conexion.execute(text("SELECT nombre FROM persona WHERE documento = 'SEMILLA-01'")).scalar_one() == "Otra Persona"


# --- El comando accesia semilla agente ---


@pytest.fixture
def transaccion_de_la_prueba(conexion: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    """db.transaccion() del comando usa la conexión de la prueba, que se deshace al terminar."""

    @contextmanager
    def transaccion() -> Iterator[Connection]:
        yield conexion

    monkeypatch.setattr("accesia.db.transaccion", transaccion)


@pytest.mark.usefixtures("transaccion_de_la_prueba")
def test_el_comando_crea_y_borra_la_semilla(conexion: Connection, capsys: pytest.CaptureFixture) -> None:
    assert principal(["semilla", "agente"]) == 0
    salida = capsys.readouterr().out
    assert "Semilla del agente lista para hoy, 2026-11-20 (hora de Colombia)" in salida
    assert "Preguntas 1 a 9 con las herramientas: 9 de 9 como dice el contrato." in salida
    assert "  ✓ 2. ¿Quién faltó ayer? Felipe Soto" in salida

    assert principal(["semilla", "agente", "--borrar"]) == 0
    assert "Semilla del agente borrada: 6 personas, 14 eventos y el horario «Clase todos los días»." in (
        capsys.readouterr().out
    )
    assert conexion.execute(text("SELECT count(*) FROM persona")).scalar_one() == 0


@pytest.mark.usefixtures("transaccion_de_la_prueba")
def test_el_comando_con_datos_reales_pide_la_opcion(conexion: Connection, capsys: pytest.CaptureFixture) -> None:
    armar.persona(conexion, documento="1075999001", nombre="Persona Real")

    assert principal(["semilla", "agente"]) == 1
    assert "--con-datos-reales" in capsys.readouterr().err

    assert principal(["semilla", "agente", "--con-datos-reales"]) == 0
    assert "no los toqué" in capsys.readouterr().out
