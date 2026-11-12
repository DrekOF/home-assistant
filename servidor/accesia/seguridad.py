"""
Nombre: seguridad.py
Descripción: Claves de los administradores con Argon2id (RNF-02 · C2) y tokens de las cámaras guardados como SHA-256 (RNF-02 · C1).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

import hashlib
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Argon2id con los parámetros recomendados de argon2-cffi.
_argon2 = PasswordHasher()


def hash_de_clave(clave: str) -> str:
    """Hash Argon2id de una clave; es lo único que guarda la base."""
    return _argon2.hash(clave)


@lru_cache
def _hash_de_relleno() -> str:
    return _argon2.hash(secrets.token_urlsafe(16))


def clave_correcta(clave_hash: str | None, clave: str) -> bool:
    """Compara la clave con su hash. Sin hash (un correo que no existe) compara igual con uno de relleno,
    para que la respuesta tarde lo mismo y no revele qué correos existen."""
    try:
        return _argon2.verify(clave_hash or _hash_de_relleno(), clave) and clave_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def token_nuevo() -> str:
    """Token de una cámara: 32 bytes aleatorios en base64 para URL (43 caracteres)."""
    return secrets.token_urlsafe(32)


def hash_de_token(token: str) -> str:
    """SHA-256 del token en hexadecimal: la base guarda esto y nunca el token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
