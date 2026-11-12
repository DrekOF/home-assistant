"""
Nombre: mensajes.py
Descripción: Frases cortas del campo mensaje de la respuesta a la cámara (api-dispositivo.md). No dependen del género de nadie y nunca nombran a quien se parece una cara (RNF-01 · C3).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
"""

DENEGADO = {
    "inactiva": "Acceso denegado: persona inactiva",
    "sin_consentimiento": "Acceso denegado: falta el consentimiento",
}
DESCONOCIDO = "No te reconozco"
DESCARTADO = {"sin_cara": "No veo una cara", "cara_pequena": "Acércate a la cámara"}
RECHAZO = {
    "sin_cara": "No veo una cara",
    "varias_caras": "Que se vea una sola cara",
    "cara_pequena": "Acércate a la cámara",
    "borrosa": "Imagen borrosa: no te muevas",
    "parece_otra_persona": "Se parece a otra persona inscrita",
    "distinta_de_la_primera": "No se parece a la primera muestra",
}


def primer_nombre(nombre: str) -> str:
    partes = nombre.split()
    return partes[0] if partes else nombre


def de_acceso(resultado: str, motivo: str | None, nombre: str | None) -> str:
    """Mensaje de permitido, denegado, desconocido o descartado. Una repetición de R4 usa el mismo."""
    if resultado == "permitido":
        return f"Hola, {primer_nombre(nombre or '')}. Puedes pasar"
    if resultado == "denegado":
        return DENEGADO[motivo or ""]
    if resultado == "desconocido":
        return DESCONOCIDO
    return DESCARTADO[motivo or ""]


def de_muestra(motivo: str | None, muestras: int, requeridas: int) -> str:
    """Mensaje de una muestra aceptada (con el avance) o rechazada (con lo que hay que corregir)."""
    if motivo is not None:
        return RECHAZO[motivo]
    if muestras >= requeridas:
        return f"Muestra {muestras} de {requeridas}: inscripción completa"
    return f"Muestra {muestras} de {requeridas}"
