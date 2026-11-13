/**
 * Nombre: validaciones.ts
 * Descripción: Validaciones de los formularios de la web con las mismas reglas de openapi.yaml y mensajes en español.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import type { TipoCamara } from '../api/cliente'
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

/** Dispositivo.codigo en openapi.yaml. */
export const PATRON_CODIGO_CAMARA = /^[a-z0-9-]{3,32}$/
/** Reservado para los temas MQTT del servidor: el servidor lo rechaza con 422 validacion (DispositivoNuevo). */
export const CODIGO_RESERVADO = 'servidor'
/** DispositivoNuevo.nombre en openapi.yaml. */
export const NOMBRE_CAMARA_MIN = 2
export const NOMBRE_CAMARA_MAX = 60

/** Una URL completa con http o https y servidor, como la que pide el modo extraer (GET {url_captura}). */
export function esUrlCaptura(texto: string): boolean {
  try {
    const url = new URL(texto)
    return (url.protocol === 'http:' || url.protocol === 'https:') && url.hostname !== ''
  } catch {
    return false
  }
}

export type CampoCamara = 'codigo' | 'nombre' | 'url'

/**
 * DispositivoNuevo y DispositivoCambios: el código solo al crear (después no cambia) y la URL de captura,
 * obligatoria si el tipo es respaldo.
 */
export function validarCamara(datos: {
  codigo?: string
  nombre: string
  tipo: TipoCamara
  url: string
}): Errores<CampoCamara> {
  const errores: Errores<CampoCamara> = {}
  if (datos.codigo !== undefined) {
    const codigo = datos.codigo.trim()
    if (!codigo) errores.codigo = 'Escribe el código de la cámara.'
    else if (codigo === CODIGO_RESERVADO) errores.codigo = '«servidor» está reservado para el servidor. Elige otro código.'
    else if (!PATRON_CODIGO_CAMARA.test(codigo)) {
      errores.codigo = 'Usa de 3 a 32 letras minúsculas, números o guiones, sin espacios ni tildes.'
    }
  }
  const nombre = limpiarNombre(datos.nombre)
  if (!nombre) errores.nombre = 'Escribe el nombre de la cámara.'
  else if (nombre.length < NOMBRE_CAMARA_MIN) errores.nombre = `El nombre necesita al menos ${NOMBRE_CAMARA_MIN} letras.`
  else if (nombre.length > NOMBRE_CAMARA_MAX) errores.nombre = `El nombre puede tener hasta ${NOMBRE_CAMARA_MAX} caracteres.`
  const url = datos.url.trim()
  if (url && !esUrlCaptura(url)) errores.url = 'Escribe una dirección completa, como http://192.168.137.50/capture.'
  else if (!url && datos.tipo === 'respaldo') errores.url = 'Una cámara de respaldo necesita su URL de captura.'
  return errores
}

export function hayErrores(errores: Record<string, string | undefined>): boolean {
  return Object.values(errores).some(Boolean)
}
