"""
Nombre: agente.py
Descripción: Las seis herramientas de solo lectura del agente (contratos/mcp-agente.md): las cinco consultas leen solo las tres vistas del agente, en una transacción READ ONLY de 3 s, y la de fecha y hora no toca la base. Devuelven lo que dice el contrato o {"error": "texto"}.
Fecha de creación: 2026-11-12
Actualización: 2026-11-13
Autor: Equipo AccesIA
Versión: 1.1

Las funciones de consulta reciben una conexión y no abren transacciones: las usan las herramientas del servidor MCP
(con el usuario agente, D-15) y la revisión de la semilla. Nunca devuelven documentos, huellas ni similitudes: las
vistas no los tienen (RNF-01 · C4).
"""

import logging
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import SQLAlchemyError

from accesia import tiempo
from accesia.config import configuracion

registro = logging.getLogger(__name__)

# Límites del contrato.
NOMBRE_MIN, NOMBRE_MAX = 2, 60
MAX_PERSONAS = 10
MAX_DIAS = 31
MAX_ACCESOS = 50
HORAS_MIN, HORAS_MAX, HORAS_POR_DEFECTO = 1, 168, 24
MAX_ULTIMOS = 10

# Cada herramienta corre en una transacción READ ONLY con este statement_timeout (mcp-agente.md, Servidor MCP).
LIMITE_CONSULTA = "3s"
TIEMPO_AGOTADO = "57014"  # SQLSTATE de query_canceled, el que da statement_timeout

DIAS_ATRAS = {"hoy": 0, "ayer": 1, "antier": 2}
DIAS_DE_LA_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
FECHA_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")

# Parte del nombre, sin importar tildes ni mayúsculas. La búsqueda escapa % y _ para que se busquen como texto.
COINCIDE_EL_NOMBRE = "unaccent(lower(nombre)) LIKE unaccent(lower(:patron)) ESCAPE '\\'"

SIN_NADIE = "No hay nadie registrado con ese nombre."
VARIAS = "Hay varias personas con ese nombre; pregunta cuál."


class ErrorDeHerramienta(Exception):
    """Un error que la herramienta devuelve como {"error": texto}: nunca sale como excepción (mcp-agente.md)."""


# --- Lectura de los parámetros ---


def hoy() -> date:
    """La fecha de hoy en Colombia: ahora() ya viene en esa zona (R8)."""
    return tiempo.ahora().date()


def leer_fecha(texto: str | None, campo: str = "fecha") -> date:
    """AAAA-MM-DD o las palabras hoy, ayer y antier, sin importar mayúsculas, calculadas en hora de Colombia."""
    valor = (texto or "").strip().lower()
    if valor in DIAS_ATRAS:
        return hoy() - timedelta(days=DIAS_ATRAS[valor])
    if FECHA_ISO.fullmatch(valor):
        try:
            return date.fromisoformat(valor)
        except ValueError:
            pass
    raise ErrorDeHerramienta(f"{campo} debe ser AAAA-MM-DD, hoy, ayer o antier (llegó «{(texto or '')[:40]}»).")


def leer_rango(desde: str | None, hasta: str | None) -> tuple[date, date]:
    inicio, fin = leer_fecha(desde, "desde"), leer_fecha(hasta, "hasta")
    if fin < inicio:
        raise ErrorDeHerramienta("hasta no puede ser anterior a desde.")
    return inicio, fin


def leer_nombre(texto: str | None) -> str:
    """El nombre buscado, sin espacios de sobra, de 2 a 60 caracteres."""
    nombre = " ".join((texto or "").split())
    if not NOMBRE_MIN <= len(nombre) <= NOMBRE_MAX:
        raise ErrorDeHerramienta(f"El nombre debe tener de {NOMBRE_MIN} a {NOMBRE_MAX} caracteres.")
    return nombre


def patron(nombre: str) -> str:
    """El nombre como parte de otro, para LIKE: \\, % y _ se buscan como texto."""
    escapado = nombre.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


# --- Formato de las horas (hora de Colombia) ---


def _hora(momento: datetime) -> str:
    return tiempo.a_colombia(momento).strftime("%H:%M")


def _fecha(momento: datetime) -> str:
    return tiempo.a_colombia(momento).date().isoformat()


def _fecha_y_hora(momento: datetime) -> str:
    return tiempo.a_colombia(momento).strftime("%Y-%m-%d %H:%M")


def _inicio_del_dia(dia: date) -> datetime:
    return datetime.combine(dia, time(0), tzinfo=configuracion().zona)


# --- Las cinco consultas ---


def buscar_persona(conexion: Connection, nombre: str) -> dict[str, Any]:
    """Hasta 10 personas cuyo nombre contiene el buscado, con su rol, si está activa y su horario."""
    buscado = leer_nombre(nombre)
    filas = conexion.execute(
        text(
            "SELECT nombre, rol, activa, horario FROM v_persona_agente "
            f"WHERE {COINCIDE_EL_NOMBRE} ORDER BY nombre LIMIT :limite"
        ),
        {"patron": patron(buscado), "limite": MAX_PERSONAS},
    ).all()
    return {
        "personas": [
            {"nombre": fila.nombre, "rol": fila.rol, "activa": fila.activa, "horario": fila.horario} for fila in filas
        ]
    }


def asistencia_del_dia(conexion: Connection, fecha: str = "hoy") -> dict[str, Any]:
    """Quién llegó a tiempo, tarde (con minutos) o sin horario, y quién faltó en la fecha.

    Ausentes: personas activas cuyo horario tiene bloque ese día de la semana (D-20) y que no tienen llegada. Las
    llegadas manuales cuentan igual que las de la cámara.
    """
    dia = leer_fecha(fecha)
    llegadas = conexion.execute(
        text(
            "SELECT nombre, llegada, estado, minutos_tarde FROM v_asistencia_agente "
            "WHERE fecha = :fecha ORDER BY llegada, nombre"
        ),
        {"fecha": dia},
    ).all()
    ausentes = conexion.execute(
        text(
            "SELECT p.nombre FROM v_persona_agente p "
            "WHERE p.activa AND CAST(:dia AS smallint) = ANY (p.dias_horario) "
            "AND NOT EXISTS (SELECT 1 FROM v_asistencia_agente a WHERE a.fecha = :fecha AND a.nombre = p.nombre) "
            "ORDER BY p.nombre"
        ),
        {"dia": dia.isoweekday(), "fecha": dia},
    ).scalars().all()

    resultado: dict[str, Any] = {"fecha": dia.isoformat(), "a_tiempo": [], "tarde": [], "sin_horario": []}
    for fila in llegadas:
        llegada: dict[str, Any] = {"nombre": fila.nombre, "llegada": _hora(fila.llegada)}
        if fila.estado == "tarde":
            llegada["minutos_tarde"] = fila.minutos_tarde
        resultado[fila.estado].append(llegada)
    resultado["ausentes"] = list(ausentes)
    resultado["total_llegadas"] = len(llegadas)
    return resultado


def llegadas_tarde(conexion: Connection, desde: str = "hoy", hasta: str = "hoy") -> dict[str, Any]:
    """Las llegadas tarde entre dos fechas, incluidas; como máximo 31 días después de desde."""
    inicio, fin = leer_rango(desde, hasta)
    if (fin - inicio).days > MAX_DIAS:
        raise ErrorDeHerramienta(f"hasta puede ser como máximo {MAX_DIAS} días después de desde.")
    filas = conexion.execute(
        text(
            "SELECT fecha, nombre, llegada, minutos_tarde FROM v_asistencia_agente "
            "WHERE estado = 'tarde' AND fecha BETWEEN :desde AND :hasta ORDER BY fecha, llegada, nombre"
        ),
        {"desde": inicio, "hasta": fin},
    ).all()
    llegadas = [
        {"fecha": fila.fecha.isoformat(), "nombre": fila.nombre, "llegada": _hora(fila.llegada),
         "minutos_tarde": fila.minutos_tarde}
        for fila in filas
    ]
    return {"desde": inicio.isoformat(), "hasta": fin.isoformat(), "llegadas": llegadas, "total": len(llegadas)}


def accesos_de_persona(conexion: Connection, nombre: str, desde: str = "hoy", hasta: str = "hoy") -> dict[str, Any]:
    """Los intentos de entrada de una persona entre dos fechas.

    Con más de 50, van los 50 más recientes, en orden de hora, y total cuenta todos (mcp-agente.md 1.3).
    """
    buscado = leer_nombre(nombre)
    inicio, fin = leer_rango(desde, hasta)
    coincidencias = conexion.execute(
        text(f"SELECT nombre FROM v_persona_agente WHERE {COINCIDE_EL_NOMBRE} ORDER BY nombre LIMIT :limite"),
        {"patron": patron(buscado), "limite": MAX_PERSONAS},
    ).scalars().all()
    if not coincidencias:
        return {"coincidencias": [], "mensaje": SIN_NADIE}
    if len(coincidencias) > 1:
        return {"coincidencias": list(coincidencias), "mensaje": VARIAS}

    persona = coincidencias[0]
    rango = {"nombre": persona, "inicio": _inicio_del_dia(inicio), "fin": _inicio_del_dia(fin + timedelta(days=1))}
    filtro = "WHERE nombre = :nombre AND fecha_hora >= :inicio AND fecha_hora < :fin"
    total = conexion.execute(text(f"SELECT count(*) FROM v_acceso_agente {filtro}"), rango).scalar_one()
    filas = conexion.execute(
        text(f"SELECT fecha_hora, camara, resultado FROM v_acceso_agente {filtro} ORDER BY fecha_hora DESC LIMIT :limite"),
        {**rango, "limite": MAX_ACCESOS},
    ).all()
    accesos = [
        {"fecha": _fecha(fila.fecha_hora), "hora": _hora(fila.fecha_hora), "camara": fila.camara,
         "resultado": fila.resultado}
        for fila in reversed(filas)
    ]
    return {"persona": persona, "accesos": accesos, "total": total}


def desconocidos_recientes(conexion: Connection, horas: int = HORAS_POR_DEFECTO) -> dict[str, Any]:
    """Las caras desconocidas de las últimas horas, por cámara.

    En ultimos van las 10 más recientes, de la más antigua a la más nueva (mcp-agente.md 1.3).
    """
    if isinstance(horas, bool) or not isinstance(horas, int) or not HORAS_MIN <= horas <= HORAS_MAX:
        raise ErrorDeHerramienta(f"horas debe ser un número entero de {HORAS_MIN} a {HORAS_MAX}.")
    ahora = tiempo.ahora()
    ventana = {"desde": ahora - timedelta(hours=horas), "hasta": ahora}
    filtro = "WHERE resultado = 'desconocido' AND fecha_hora >= :desde AND fecha_hora <= :hasta"
    por_camara = {
        camara: cantidad
        for camara, cantidad in conexion.execute(
            text(f"SELECT camara, count(*) FROM v_acceso_agente {filtro} GROUP BY camara ORDER BY camara"), ventana
        )
    }
    ultimos = conexion.execute(
        text(f"SELECT fecha_hora FROM v_acceso_agente {filtro} ORDER BY fecha_hora DESC LIMIT :limite"),
        {**ventana, "limite": MAX_ULTIMOS},
    ).scalars().all()
    return {
        "horas": horas,
        "total": sum(por_camara.values()),
        "por_camara": por_camara,
        "ultimos": [_fecha_y_hora(momento) for momento in reversed(ultimos)],
    }


# --- La fecha y la hora (mcp-agente.md 1.5) ---


def fecha_y_hora() -> dict[str, Any]:
    """La fecha, el día de la semana y la hora de ahora en Colombia (R8). No toca la base."""
    ahora = tiempo.a_colombia(tiempo.ahora())
    return {"fecha": _fecha(ahora), "dia": DIAS_DE_LA_SEMANA[ahora.weekday()], "hora": _hora(ahora)}


# --- Las herramientas: una transacción de solo lectura por llamada ---


@contextmanager
def transaccion_de_lectura(motor: Engine) -> Iterator[Connection]:
    """Una transacción READ ONLY con statement_timeout de 3 s (D-15): ni con el dueño de la base se podría escribir."""
    with motor.connect() as conexion, conexion.begin():
        conexion.exec_driver_sql("SET TRANSACTION READ ONLY")
        conexion.exec_driver_sql(f"SET LOCAL statement_timeout = '{LIMITE_CONSULTA}'")
        yield conexion


class Herramientas:
    """Las seis herramientas del contrato. Las cinco consultas usan un motor de la base: en el servidor MCP, el
    del usuario agente, con una transacción de solo lectura por llamada. La de fecha y hora no toca la base.

    Ninguna lanza: un error vuelve como {"error": …}.
    """

    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def buscar_persona(self, nombre: str) -> dict[str, Any]:
        return self._responder(buscar_persona, nombre=nombre)

    def asistencia_del_dia(self, fecha: str = "hoy") -> dict[str, Any]:
        return self._responder(asistencia_del_dia, fecha=fecha)

    def llegadas_tarde(self, desde: str = "hoy", hasta: str = "hoy") -> dict[str, Any]:
        return self._responder(llegadas_tarde, desde=desde, hasta=hasta)

    def accesos_de_persona(self, nombre: str, desde: str = "hoy", hasta: str = "hoy") -> dict[str, Any]:
        return self._responder(accesos_de_persona, nombre=nombre, desde=desde, hasta=hasta)

    def desconocidos_recientes(self, horas: int = HORAS_POR_DEFECTO) -> dict[str, Any]:
        return self._responder(desconocidos_recientes, horas=horas)

    def fecha_y_hora(self) -> dict[str, Any]:
        try:
            return fecha_y_hora()
        except Exception:  # noqa: BLE001 — el contrato pide {"error": …}, nunca una excepción
            registro.exception("Error inesperado en la herramienta fecha_y_hora")
            return {"error": "La herramienta falló. Intenta de nuevo en un momento."}

    def _responder(self, consulta: Callable[..., dict[str, Any]], **argumentos: Any) -> dict[str, Any]:
        try:
            with transaccion_de_lectura(self._motor) as conexion:
                return consulta(conexion, **argumentos)
        except ErrorDeHerramienta as error:
            return {"error": str(error)}
        except SQLAlchemyError as error:
            if getattr(getattr(error, "orig", None), "sqlstate", None) == TIEMPO_AGOTADO:
                return {"error": f"La consulta tardó más de {LIMITE_CONSULTA.removesuffix('s')} s. Prueba con menos días."}
            registro.warning("La herramienta %s no pudo consultar la base: %s", consulta.__name__, type(error).__name__)
            return {"error": "No se pudo consultar la base de AccesIA. Intenta de nuevo en un momento."}
        except Exception:  # noqa: BLE001 — el contrato pide {"error": …}, nunca una excepción
            registro.exception("Error inesperado en la herramienta %s", consulta.__name__)
            return {"error": "La herramienta falló. Intenta de nuevo en un momento."}
