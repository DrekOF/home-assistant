"""
Nombre: test_web.py
Descripción: Pruebas «D-04 · web servida» (la web compilada sale del mismo servidor, con su tipo y su caché, y nunca sirve un archivo de fuera de dist) y «contrato API · error» con la web encendida (la API responde igual que sin ella).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

from pathlib import Path
from urllib.parse import quote

import pytest
from esquemas import validar
from fastapi.testclient import TestClient

from accesia.main import crear_app

INDICE = (
    '<!doctype html><html lang="es"><head><title>AccesIA</title>'
    '<script type="module" src="/assets/index-abc123.js"></script></head><body><div id="raiz"></div></body></html>'
)
CACHE_INMUTABLE = "public, max-age=31536000, immutable"
SECRETO = "secreto de prueba: nunca sale por la web"


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    """Una web compilada mínima, como la que deja npm run build, con un archivo secreto al lado, fuera de dist."""
    carpeta = tmp_path / "dist"
    (carpeta / "assets").mkdir(parents=True)
    (carpeta / "index.html").write_text(INDICE, encoding="utf-8")
    (carpeta / "favicon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    (carpeta / "assets" / "index-abc123.js").write_text('console.log("AccesIA")', encoding="utf-8")
    (carpeta / "assets" / "index-abc123.css").write_text("body{margin:0}", encoding="utf-8")
    (carpeta / "assets" / "fuente-abc123.woff2").write_bytes(b"wOF2 de prueba")
    (tmp_path / "secreto.txt").write_text(SECRETO, encoding="utf-8")
    return carpeta


@pytest.fixture
def web(dist: Path) -> TestClient:
    """La app con la web encendida. No corre el arranque: estas pruebas no usan la base."""
    return TestClient(crear_app(carpeta_web=dist))


def es_la_web(respuesta) -> None:
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "text/html; charset=utf-8"
    assert respuesta.text == INDICE
    assert respuesta.headers["cache-control"] == "no-cache", "index.html se revisa en cada visita."
    assert respuesta.headers["x-content-type-options"] == "nosniff"


# --- D-04 · web servida ---


@pytest.mark.marca("D-04 · web servida")
def test_la_raiz_devuelve_la_web_sin_cache_larga(web: TestClient) -> None:
    es_la_web(web.get("/"))


@pytest.mark.marca("D-04 · web servida")
@pytest.mark.parametrize(
    ("ruta", "tipo"),
    [
        ("/assets/index-abc123.js", "text/javascript; charset=utf-8"),
        ("/assets/index-abc123.css", "text/css; charset=utf-8"),
        ("/assets/fuente-abc123.woff2", "font/woff2"),
    ],
)
def test_un_archivo_de_assets_sale_con_su_tipo_y_cache_larga(web: TestClient, ruta: str, tipo: str) -> None:
    respuesta = web.get(ruta)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == tipo
    assert respuesta.headers["cache-control"] == CACHE_INMUTABLE, "Vite les pone hash: no cambian nunca."
    assert respuesta.headers["x-content-type-options"] == "nosniff"


@pytest.mark.marca("D-04 · web servida")
def test_el_favicon_sale_con_su_tipo_y_sin_cache_larga(web: TestClient) -> None:
    respuesta = web.get("/favicon.svg")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/svg+xml"
    assert respuesta.headers["cache-control"] == "no-cache", "Fuera de assets/ no hay hash: se revisa cada vez."
    assert respuesta.headers["x-content-type-options"] == "nosniff"


@pytest.mark.marca("D-04 · web servida")
@pytest.mark.parametrize(
    "ruta",
    [
        "/entrar",
        "/personas",
        "/personas/3f2a9c1e-0000-4000-8000-000000000001/editar",
        "/camaras/entrada",
        "/asistencia?fecha=2026-11-20",
    ],
)
def test_una_ruta_del_navegador_recargada_devuelve_la_web(web: TestClient, ruta: str) -> None:
    # La web usa createBrowserRouter: al recargar /personas, el servidor debe devolver index.html.
    es_la_web(web.get(ruta))


@pytest.mark.marca("D-04 · web servida")
def test_head_de_la_raiz_responde_sin_cuerpo(web: TestClient) -> None:
    respuesta = web.head("/")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "text/html; charset=utf-8"
    assert respuesta.headers["content-length"] == str(len(INDICE.encode()))
    assert respuesta.content == b""


@pytest.mark.marca("D-04 · web servida")
def test_un_archivo_que_falta_en_assets_da_404_y_no_la_web(web: TestClient) -> None:
    # Un archivo con hash que ya no existe (por ejemplo, de una versión anterior) no se cambia por index.html.
    respuesta = web.get("/assets/index-viejo.js")

    assert respuesta.status_code == 404
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "no_encontrado"


@pytest.mark.marca("D-04 · web servida")
@pytest.mark.parametrize(
    "ruta",
    [
        "/%2e%2e/secreto.txt",
        "/assets/%2e%2e/%2e%2e/secreto.txt",
        "/..%2fsecreto.txt",
        "/..%5csecreto.txt",
        "/%00",
    ],
)
def test_una_ruta_con_puntos_nunca_sirve_un_archivo_de_fuera_de_dist(web: TestClient, ruta: str) -> None:
    respuesta = web.get(ruta)

    assert respuesta.status_code in (200, 404)
    assert SECRETO not in respuesta.text


@pytest.mark.marca("D-04 · web servida")
def test_una_ruta_absoluta_nunca_sirve_un_archivo_de_fuera_de_dist(web: TestClient, dist: Path) -> None:
    # En Windows, C:\...\secreto.txt pegado a dist reemplaza la carpeta entera si no se revisa.
    respuesta = web.get("/" + quote(str(dist.parent / "secreto.txt"), safe=""))

    assert respuesta.status_code in (200, 404)
    assert SECRETO not in respuesta.text


@pytest.mark.marca("D-04 · web servida")
def test_sin_la_web_compilada_la_raiz_da_404_y_la_api_sigue(url_base: str, tmp_path: Path) -> None:
    cliente = TestClient(crear_app(carpeta_web=tmp_path / "sin-web"))

    raiz = cliente.get("/")
    assert raiz.status_code == 404
    validar("Error", raiz.json())
    assert raiz.json()["codigo"] == "no_encontrado"
    assert cliente.get("/api/v1/salud").status_code == 200


# --- contrato API · error, con la web encendida ---


@pytest.mark.marca("contrato API · error")
@pytest.mark.parametrize("metodo", ["GET", "HEAD", "POST"])
@pytest.mark.parametrize("ruta", ["/api/v1/no-existe", "/api/no-existe", "/api"])
def test_con_la_web_una_ruta_de_la_api_que_no_existe_sigue_dando_404(web: TestClient, metodo: str, ruta: str) -> None:
    respuesta = web.request(metodo, ruta)

    assert respuesta.status_code == 404
    if metodo != "HEAD":
        validar("Error", respuesta.json())
        assert respuesta.json()["codigo"] == "no_encontrado"


@pytest.mark.marca("contrato API · error")
def test_con_la_web_un_metodo_que_la_ruta_no_acepta_sigue_dando_405(web: TestClient) -> None:
    respuesta = web.delete("/api/v1/salud")

    assert respuesta.status_code == 405
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "metodo_no_permitido"
    assert "GET" in respuesta.headers["allow"], "El 405 conserva la cabecera Allow."


@pytest.mark.marca("contrato API · error")
def test_con_la_web_un_post_a_una_ruta_de_la_web_da_404(web: TestClient) -> None:
    respuesta = web.post("/personas", json={})

    assert respuesta.status_code == 404
    validar("Error", respuesta.json())
    assert respuesta.json()["codigo"] == "no_encontrado"


@pytest.mark.marca("contrato API · error")
def test_con_la_web_una_ruta_que_se_agrega_despues_sigue_respondiendo(dist: Path) -> None:
    app = crear_app(carpeta_web=dist)

    @app.get("/prueba/despues")
    def ruta_de_prueba() -> dict[str, bool]:
        return {"responde": True}

    respuesta = TestClient(app).get("/prueba/despues")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"responde": True}
