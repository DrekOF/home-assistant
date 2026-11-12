"""
Nombre: envio.py
Descripción: Envío de cada recorte al servidor según specs/contratos/api-dispositivo.md: POST con las cuatro cabeceras y tiempo de espera de 5 s.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from simulador import FIRMWARE

# «Sin respuesta en 5 s» (api-dispositivo.md, Qué hace la cámara con la respuesta).
TIEMPO_ESPERA_S = 5.0


@dataclass(frozen=True)
class Respuesta:
    """Lo que pasó con un envío.

    `estado` es el código HTTP, o None si no hubo respuesta; entonces `falla` dice por qué.
    """

    estado: int | None
    cuerpo: dict[str, Any] | None = None
    retry_after: str | None = None
    falla: str | None = None

    @property
    def resultado(self) -> str | None:
        """El `resultado` de una respuesta 200; None en los errores."""
        if self.estado == 200 and self.cuerpo is not None:
            return self.cuerpo.get("resultado")
        return None


class ClienteCamara:
    """Habla con el servidor como la cámara. El token se usa solo en la cabecera: nunca se muestra ni se guarda."""

    def __init__(
        self,
        servidor: str,
        codigo: str,
        token: str,
        *,
        transporte: httpx.BaseTransport | None = None,
        tiempo_espera: float = TIEMPO_ESPERA_S,
    ) -> None:
        self.url = f"{servidor.rstrip('/')}/api/v1/dispositivos/{quote(codigo, safe='')}/rostros"
        self.tiempo_espera = tiempo_espera
        self._token = token
        self._http = httpx.Client(timeout=tiempo_espera, transport=transporte)

    def enviar(self, jpeg: bytes, puntaje: float | None) -> Respuesta:
        cabeceras = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "image/jpeg",
            "X-AccesIA-Firmware": FIRMWARE,
        }
        if puntaje is not None:
            cabeceras["X-AccesIA-Puntaje"] = f"{min(max(puntaje, 0.0), 1.0):.3f}"

        try:
            respuesta = self._http.post(self.url, content=jpeg, headers=cabeceras)
        except httpx.TimeoutException:
            return Respuesta(None, falla=f"sin respuesta en {self.tiempo_espera:g} s")
        except (httpx.HTTPError, httpx.InvalidURL) as error:
            return Respuesta(None, falla=f"no se pudo conectar con el servidor ({type(error).__name__})")

        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = None
        return Respuesta(
            respuesta.status_code,
            cuerpo if isinstance(cuerpo, dict) else None,
            respuesta.headers.get("Retry-After"),
        )

    def cerrar(self) -> None:
        self._http.close()
