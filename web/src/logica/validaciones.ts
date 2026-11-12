/**
 * Nombre: validaciones.ts
 * Descripción: Validaciones de los formularios de la web con las mismas reglas de openapi.yaml y mensajes en español.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { aIsoColombia, esFutura } from './fechas'

/** Persona.documento en openapi.yaml. */
export const PATRON_DOCUMENTO = /^[0-9A-Za-z-]{3,20}$/
/** Persona.nombre en openapi.yaml. */
export const NOMBRE_MIN = 2
export const NOMBRE_MAX = 120
/** Credenciales.clave en openapi.yaml. */
export const CLAVE_MIN = 8

const PATRON_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export type Errores<Campo extends string> = Partial<Record<Campo, string>>

/** Quita los espacios de los extremos y deja uno solo entre palabras. */
export function limpiarNombre(nombre: string): string {
  return nombre.trim().replace(/\s+/g, ' ')
}

export function validarCredenciales(datos: { correo: string; clave: string }): Errores<'correo' | 'clave'> {
  const errores: Errores<'correo' | 'clave'> = {}
  const correo = datos.correo.trim()
  if (!correo) errores.correo = 'Escribe tu correo.'
  else if (!PATRON_CORREO.test(correo)) errores.correo = 'Escribe un correo válido, como nombre@dominio.co.'
  if (!datos.clave) errores.clave = 'Escribe tu clave.'
  else if (datos.clave.length < CLAVE_MIN) errores.clave = `La clave tiene al menos ${CLAVE_MIN} caracteres.`
  return errores
}

export function validarPersona(datos: { nombre: string; documento: string }): Errores<'nombre' | 'documento'> {
  const errores: Errores<'nombre' | 'documento'> = {}
  const nombre = limpiarNombre(datos.nombre)
  const documento = datos.documento.trim()
  if (!nombre) errores.nombre = 'Escribe el nombre completo.'
  else if (nombre.length < NOMBRE_MIN) errores.nombre = `El nombre necesita al menos ${NOMBRE_MIN} letras.`
  else if (nombre.length > NOMBRE_MAX) errores.nombre = `El nombre puede tener hasta ${NOMBRE_MAX} caracteres.`
  if (!documento) errores.documento = 'Escribe el número de documento.'
  else if (!PATRON_DOCUMENTO.test(documento)) {
    errores.documento = 'Usa de 3 a 20 letras, números o guiones, sin espacios ni puntos.'
  }
  return errores
}

export type MedioConsentimiento = 'web' | 'papel'

/** ConsentimientoNuevo: acepta debe ser true; aceptado_en solo con papel y no puede ser futura. */
export function validarConsentimiento(
  datos: { medio: MedioConsentimiento; acepta: boolean; aceptadoEn: string },
  ahora: Date = new Date(),
): Errores<'acepta' | 'aceptadoEn'> {
  const errores: Errores<'acepta' | 'aceptadoEn'> = {}
  if (!datos.acepta) errores.acepta = 'Marca la casilla solo cuando la persona haya aceptado.'
  if (datos.medio === 'papel') {
    if (!datos.aceptadoEn) errores.aceptadoEn = 'Escribe la fecha y la hora en que la persona firmó.'
    else {
      const iso = aIsoColombia(datos.aceptadoEn)
      if (!iso) errores.aceptadoEn = 'Escribe una fecha y una hora válidas.'
      else if (esFutura(iso, ahora)) errores.aceptadoEn = 'La fecha de la firma no puede ser futura.'
    }
  }
  return errores
}

export function hayErrores(errores: Record<string, string | undefined>): boolean {
  return Object.values(errores).some(Boolean)
}
