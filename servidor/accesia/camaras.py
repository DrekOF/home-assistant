"""
Nombre: camaras.py
Descripción: Cámaras de AccesIA (RF-10 · C1 a C3 y C5): crear con su token, ver con su estado e inscripción activa, editar y cambiar el token. Las usan la API y el comando crear-camara.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from datetime import datetime, timedelta

from sqlalchemy import Connection, Row, text
from sqlalchemy.exc import IntegrityError

from accesia.db import VIOLACION_UNICA, violacion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import (
    Dispositivo,
    DispositivoCambios,
    DispositivoConToken,
    DispositivoNuevo,
    InscripcionCorta,
)
from accesia.inscripciones import vencer_inscripciones
from accesia.seguridad import hash_de_token, token_nuevo
from accesia.tiempo import ahora

# Hasta que llegue MQTT (Día 3), una cámara está en línea si hizo contacto en los últimos 2 minutos.
EN_LINEA = timedelta(minutes=2)

CONSULTA = """
SELECT d.codigo, d.nombre, d.tipo, d.url_captura, d.activo, d.ultimo_contacto, d.creado,
       i.id AS inscripcion_id, i.muestras, i.requeridas, i.estado AS inscripcion_estado, i.vence
FROM dispositivo d
LEFT JOIN inscripcion i ON i.dispositivo_codigo = d.codigo AND i.estado = 'activa'
"""

# Campos de DispositivoCambios que se pueden escribir: la lista es cerrada, nunca sale de la petición.
CAMPOS_EDITABLES = ("nombre", "tipo", "url_captura", "activo")


def _a_dispositivo(fila: Row, momento: datetime) -> Dispositivo:
    activa = None
    if fila.inscripcion_id is not None:
        activa = InscripcionCorta(
            id=fila.inscripcion_id,
            muestras=fila.muestras,
            requeridas=fila.requeridas,
            estado=fila.inscripcion_estado,
            vence=fila.vence,
        )
    return Dispositivo(
        codigo=fila.codigo,
        nombre=fila.nombre,
        tipo=fila.tipo,
        url_captura=fila.url_captura,
        activo=fila.activo,
        en_linea=fila.ultimo_contacto is not None and momento - fila.ultimo_contacto <= EN_LINEA,
        modo="inscribir" if activa else "reconocer",
        inscripcion_activa=activa,
        ultimo_contacto=fila.ultimo_contacto,
        estado=None,  # el estado que publica la cámara por MQTT llega el Día 3
        creado=fila.creado,
    )


def listar(conexion: Connection) -> list[Dispositivo]:
    """Todas las cámaras, después de vencer las inscripciones que ya pasaron su hora (R9)."""
    momento = ahora()
    vencer_inscripciones(conexion, momento)
    filas = conexion.execute(text(CONSULTA + " ORDER BY d.codigo")).all()
    return [_a_dispositivo(fila, momento) for fila in filas]


def ver(conexion: Connection, codigo: str) -> Dispositivo | None:
    """Una cámara, después de vencer su inscripción si ya pasó su hora (R9); None si no existe."""
    momento = ahora()
    vencer_inscripciones(conexion, momento, codigo)
    fila = conexion.execute(text(CONSULTA + " WHERE d.codigo = :codigo"), {"codigo": codigo}).one_or_none()
    return None if fila is None else _a_dispositivo(fila, momento)


def _con_token(dispositivo: Dispositivo, token: str) -> DispositivoConToken:
    return DispositivoConToken.model_validate({**dict(dispositivo), "token": token})


def crear(conexion: Connection, datos: DispositivoNuevo) -> DispositivoConToken:
    """Registra la cámara y devuelve su token, que no se vuelve a mostrar: la base guarda solo su SHA-256."""
    token = token_nuevo()
    try:
        with conexion.begin_nested():
            conexion.execute(
                text(
                    "INSERT INTO dispositivo (codigo, nombre, tipo, token_hash, url_captura) "
                    "VALUES (:codigo, :nombre, :tipo, :token_hash, :url_captura)"
                ),
                {**datos.model_dump(), "token_hash": hash_de_token(token)},
            )
    except IntegrityError as error:
        if violacion(error) == VIOLACION_UNICA:
            raise ErrorAccesIA(409, "codigo_duplicado", f"Ya hay una cámara con el código {datos.codigo}.") from None
        raise
    dispositivo = ver(conexion, datos.codigo)
    assert dispositivo is not None
    return _con_token(dispositivo, token)


def cambiar_token(conexion: Connection, codigo: str) -> DispositivoConToken | None:
    """Genera un token nuevo; el anterior deja de servir porque su hash ya no está (RF-10 · C2)."""
    token = token_nuevo()
    cambiada = conexion.execute(
        text("UPDATE dispositivo SET token_hash = :token_hash WHERE codigo = :codigo RETURNING codigo"),
        {"token_hash": hash_de_token(token), "codigo": codigo},
    ).one_or_none()
    if cambiada is None:
        return None
    dispositivo = ver(conexion, codigo)
    assert dispositivo is not None
    return _con_token(dispositivo, token)


def editar(conexion: Connection, codigo: str, cambios: DispositivoCambios) -> Dispositivo | None:
    """Cambia nombre, tipo, URL de captura o si está activa; None si la cámara no existe."""
    actual = conexion.execute(
        text("SELECT tipo, url_captura FROM dispositivo WHERE codigo = :codigo"), {"codigo": codigo}
    ).one_or_none()
    if actual is None:
        return None
    valores = {campo: valor for campo, valor in cambios.valores().items() if campo in CAMPOS_EDITABLES}
    tipo = valores.get("tipo", actual.tipo)
    url_captura = valores.get("url_captura", actual.url_captura)
    if tipo == "respaldo" and url_captura is None:
        raise ErrorAccesIA(422, "validacion", "Una cámara de respaldo necesita su URL de captura.")
    asignaciones = ", ".join(f"{campo} = :{campo}" for campo in valores)
    conexion.execute(text(f"UPDATE dispositivo SET {asignaciones} WHERE codigo = :codigo"), {**valores, "codigo": codigo})
    return ver(conexion, codigo)
