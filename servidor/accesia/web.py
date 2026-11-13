"""
Nombre: web.py
Descripción: La web de administración compilada (web/dist) servida por el mismo servidor (D-04): un middleware ASGI que deja responder primero a la API y solo cambia por la web los 404 de GET y HEAD fuera de /api.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0

Por qué un middleware y no una ruta comodín /{ruta:path}: la ruta comodín respondería antes que las rutas que se
agregan después de crear la app, y cambiaría el 404 y el 405 de la API. Con el middleware, /api responde exactamente
como dice openapi.yaml, con la web o sin ella.
"""

import mimetypes
from pathlib import Path

from starlette.responses import FileResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Vite les pone hash a los archivos de dist/assets/: no cambian nunca, así que el navegador los guarda un año.
CACHE_INMUTABLE = "public, max-age=31536000, immutable"
# index.html y lo demás de dist no llevan hash: el navegador los revisa en cada visita y ve enseguida una web nueva.
CACHE_REVISAR = "no-cache"

# El tipo de los archivos que deja npm run build. No se le deja todo a mimetypes: en Windows (uv run en el PC) lee el
# registro, que puede cambiar el de .js, y no conoce .woff2.
TIPOS = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".json": "application/json",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".txt": "text/plain",
}


def carpeta_de_la_web() -> Path:
    """web/dist desde la raíz del repositorio, como los modelos: en el PC es <repositorio>/web/dist (npm run build);
    en la imagen, donde el servidor vive en /app/servidor, es /app/web/dist."""
    return Path(__file__).resolve().parents[2] / "web" / "dist"


def es_de_la_api(ruta: str) -> bool:
    return ruta == "/api" or ruta.startswith("/api/")


class WebCompilada:
    """Primero responde la app. Si un GET o un HEAD fuera de /api termina en 404, responde la web en su lugar."""

    def __init__(self, app: ASGIApp, carpeta: Path) -> None:
        self.app = app
        self.carpeta = carpeta.resolve()
        self.assets = self.carpeta / "assets"
        self.indice = self.carpeta / "index.html"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in ("GET", "HEAD") or es_de_la_api(scope["path"]):
            await self.app(scope, receive, send)
            return

        archivo: Path | None = None

        async def enviar(mensaje: Message) -> None:
            nonlocal archivo
            if mensaje["type"] == "http.response.start" and mensaje["status"] == 404:
                archivo = self.archivo_para(scope["path"])
            # Si la web tiene qué responder, el 404 de la app (su inicio y su cuerpo) no sale.
            if archivo is None:
                await send(mensaje)

        await self.app(scope, receive, enviar)
        if archivo is not None:
            await self.respuesta(archivo)(scope, receive, send)

    def archivo_para(self, ruta: str) -> Path | None:
        """El archivo de dist que se pidió o index.html, porque la web usa createBrowserRouter y una ruta del navegador
        (por ejemplo /personas al recargar) llega aquí. None deja el 404 de la app."""
        try:
            pedido = (self.carpeta / ruta.lstrip("/")).resolve()
        except (OSError, ValueError):  # una ruta que el sistema de archivos no acepta, por ejemplo con \0
            return self.indice
        # Nunca sale de dist: ni con .., ni con \ en Windows, ni con una ruta absoluta pegada a la carpeta.
        if pedido.is_relative_to(self.carpeta) and pedido.is_file():
            return pedido
        if pedido.is_relative_to(self.assets):
            return None  # un archivo con hash que ya no existe da 404: index.html no se hace pasar por JS o CSS
        return self.indice

    def respuesta(self, archivo: Path) -> FileResponse:
        # La caché depende del archivo que sale, no de la ruta pedida: index.html nunca se guarda un año.
        cache = CACHE_INMUTABLE if archivo.is_relative_to(self.assets) else CACHE_REVISAR
        tipo = TIPOS.get(archivo.suffix.lower()) or mimetypes.guess_type(archivo.name)[0] or "application/octet-stream"
        return FileResponse(
            archivo, media_type=tipo, headers={"Cache-Control": cache, "X-Content-Type-Options": "nosniff"}
        )
