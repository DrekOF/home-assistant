"""
Nombre: test_comandos.py
Descripción: Pruebas del comando accesia crear-camara (RF-10 · C5): registra la cámara, muestra el token una sola vez y valida como la API.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Connection, text

from accesia.comandos import principal


@pytest.fixture(autouse=True)
def transaccion_de_la_prueba(conexion: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    """El comando escribe en la transacción de la prueba, que se deshace al final."""

    @contextmanager
    def transaccion() -> Iterator[Connection]:
        with conexion.begin_nested():
            yield conexion

    monkeypatch.setattr("accesia.db.transaccion", transaccion)


@pytest.mark.marca("RF-10 · C5")
def test_crear_camara_muestra_el_token_una_vez_y_guarda_su_hash(conexion: Connection, capsys) -> None:
    codigo = principal(["crear-camara", "entrada", "--nombre", "Entrada", "--tipo", "simulador"])

    salida = capsys.readouterr().out.strip().splitlines()
    assert codigo == 0
    token = salida[-1]
    fila = conexion.execute(text("SELECT nombre, tipo, token_hash FROM dispositivo WHERE codigo = 'entrada'")).one()
    assert (fila.nombre, fila.tipo) == ("Entrada", "simulador")
    assert fila.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert " " not in token, "La última línea es solo el token, para copiarlo sin errores."
    assert any("solo esta vez" in linea for linea in salida)


@pytest.mark.marca("RF-10 · C5")
def test_crear_camara_de_respaldo_con_su_url(conexion: Connection) -> None:
    codigo = principal(
        ["crear-camara", "respaldo-1", "--nombre", "Respaldo", "--tipo", "respaldo", "--url-captura", "http://10.42.0.30/capture"]
    )

    assert codigo == 0
    url = conexion.execute(text("SELECT url_captura FROM dispositivo WHERE codigo = 'respaldo-1'")).scalar_one()
    assert url == "http://10.42.0.30/capture"


@pytest.mark.marca("RF-10 · C5")
@pytest.mark.parametrize(
    ("argumentos", "mensaje"),
    [
        (["servidor", "--nombre", "Servidor", "--tipo", "simulador"], "reservado"),
        (["Entrada", "--nombre", "Entrada", "--tipo", "simulador"], "letras minúsculas"),
        (["respaldo-1", "--nombre", "Respaldo", "--tipo", "respaldo"], "URL de captura"),
    ],
)
def test_crear_camara_valida_como_la_api(conexion: Connection, capsys, argumentos: list[str], mensaje: str) -> None:
    codigo = principal(["crear-camara", *argumentos])

    assert codigo == 1
    assert mensaje in capsys.readouterr().err
    assert conexion.execute(text("SELECT count(*) FROM dispositivo")).scalar_one() == 0


@pytest.mark.marca("RF-10 · C5")
def test_crear_camara_con_un_codigo_repetido_no_cambia_la_que_existe(conexion: Connection, capsys) -> None:
    assert principal(["crear-camara", "entrada", "--nombre", "Entrada", "--tipo", "simulador"]) == 0
    antes = conexion.execute(text("SELECT token_hash FROM dispositivo WHERE codigo = 'entrada'")).scalar_one()

    codigo = principal(["crear-camara", "entrada", "--nombre", "Otra", "--tipo", "tinyml"])

    assert codigo == 1
    assert "Ya hay una cámara con el código entrada" in capsys.readouterr().err
    despues = conexion.execute(text("SELECT nombre, token_hash FROM dispositivo WHERE codigo = 'entrada'")).one()
    assert (despues.nombre, despues.token_hash) == ("Entrada", antes)


@pytest.mark.marca("RF-10 · C5")
def test_crear_camara_pide_nombre_y_tipo() -> None:
    with pytest.raises(SystemExit) as salida:
        principal(["crear-camara", "entrada"])

    assert salida.value.code == 2
