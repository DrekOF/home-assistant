"""
Nombre: sesion.py
Descripción: Sesión de la web con la cookie accesia_sesion firmada (RNF-02 · C2 y C5) y creación del primer administrador.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import Connection, text

from accesia.config import configuracion
from accesia.db import Conexion
from accesia.errores import ErrorAccesIA
from accesia.esquemas import Administrador
from accesia.seguridad import hash_de_clave

registro = logging.getLogger(__name__)

COOKIE = "accesia_sesion"
DURACION_S = 8 * 60 * 60  # 8 horas desde el último uso: cada respuesta con sesión renueva la cookie
SAL = "accesia-sesion"
NOMBRE_PRIMER_ADMINISTRADOR = "Administrador"
CLAVE_MINIMA = 8  # la misma de Credenciales.clave en openapi.yaml


def _firmador() -> URLSafeTimedSerializer:
    secreto = configuracion().sesion_secreto
    if secreto is None or not secreto.get_secret_value():
        raise RuntimeError("Falta SESION_SECRETO en infra/.env: sin ella no hay sesión de la web.")
    return URLSafeTimedSerializer(secreto.get_secret_value(), salt=SAL)


def abrir_sesion(respuesta: Response, administrador_id: UUID) -> None:
    """Deja la cookie de sesión: firmada, HttpOnly, SameSite=Strict y Path=/, como pide openapi.yaml."""
    respuesta.set_cookie(
        COOKIE,
        _firmador().dumps(str(administrador_id)),
        max_age=DURACION_S,
        path="/",
        httponly=True,
        samesite="strict",
    )


def cerrar_sesion(respuesta: Response) -> None:
    respuesta.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")


def _sin_sesion() -> ErrorAccesIA:
    return ErrorAccesIA(401, "sin_sesion", "Inicia sesión para continuar.")


def administrador_actual(request: Request, respuesta: Response, conexion: Conexion) -> Administrador:
    """Dependencia de las rutas con sesión: el administrador de la cookie, o 401 sin_sesion (RNF-02 · C5)."""
    valor = request.cookies.get(COOKIE)
    if not valor:
        raise _sin_sesion()
    try:
        administrador_id = UUID(_firmador().loads(valor, max_age=DURACION_S))
    except (BadSignature, ValueError):
        # Firma falsa, cookie vencida o contenido que no es un id.
        raise _sin_sesion() from None
    fila = conexion.execute(
        text("SELECT id, correo, nombre FROM administrador WHERE id = :id AND activo"), {"id": administrador_id}
    ).one_or_none()
    if fila is None:
        raise _sin_sesion()
    abrir_sesion(respuesta, fila.id)
    return Administrador(id=fila.id, correo=fila.correo, nombre=fila.nombre)


AdministradorDeLaSesion = Annotated[Administrador, Depends(administrador_actual)]


def crear_primer_administrador(conexion: Connection, correo: str | None, clave: str | None) -> bool:
    """Crea el administrador de ADMIN_CORREO con ADMIN_CLAVE_INICIAL si no existe. Si ya existe, no toca su clave.

    Devuelve True si lo creó. Si faltan los datos o no sirven, lo dice en el registro y no crea a nadie.
    """
    if not correo or not clave:
        registro.warning("Faltan ADMIN_CORREO o ADMIN_CLAVE_INICIAL en infra/.env: no se crea el primer administrador.")
        return False
    try:
        correo = TypeAdapter(EmailStr).validate_python(correo.strip()).lower()
    except ValidationError:
        registro.error("ADMIN_CORREO no es un correo válido (un dominio .local no sirve): no se crea el administrador.")
        return False
    if len(clave) < CLAVE_MINIMA:
        registro.error("ADMIN_CLAVE_INICIAL tiene menos de %d caracteres: no se crea el administrador.", CLAVE_MINIMA)
        return False
    existe = conexion.execute(
        text("SELECT 1 FROM administrador WHERE lower(correo) = :correo"), {"correo": correo}
    ).first()
    if existe:
        return False
    conexion.execute(
        text("INSERT INTO administrador (correo, clave_hash, nombre) VALUES (:correo, :clave_hash, :nombre)"),
        {"correo": correo, "clave_hash": hash_de_clave(clave), "nombre": NOMBRE_PRIMER_ADMINISTRADOR},
    )
    registro.info("Se creó el primer administrador con ADMIN_CORREO.")
    return True
