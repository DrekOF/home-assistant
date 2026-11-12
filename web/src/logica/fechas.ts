/**
 * Nombre: fechas.ts
 * Descripción: Formato de fechas y horas en es-CO con la hora de Colombia, y conversión a ISO 8601 con zona (R8).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

export const ZONA_HORARIA = 'America/Bogota'
export const IDIOMA = 'es-CO'

// Colombia usa UTC−5 todo el año: no tiene horario de verano.
const DESFASE = '-05:00'
const DESFASE_MS = 5 * 60 * 60 * 1000

const formatoFechaHora = new Intl.DateTimeFormat(IDIOMA, {
  timeZone: ZONA_HORARIA,
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

const formatoFecha = new Intl.DateTimeFormat(IDIOMA, {
  timeZone: ZONA_HORARIA,
  dateStyle: 'long',
})

/** «20 de nov de 2026, 7:58 a. m.», en hora de Colombia. La hora y «a. m.» nunca se parten de línea. */
export function formatearFechaHora(iso: string): string {
  return formatoFechaHora
    .format(new Date(iso))
    .replace(/(\d)[\s\u00a0\u202f]*([ap])\.[\s\u00a0\u202f]*m\./g, '$1\u00a0$2.\u00a0m.')
}

/** «20 de noviembre de 2026», en hora de Colombia. */
export function formatearFecha(iso: string): string {
  return formatoFecha.format(new Date(iso))
}

const PATRON_LOCAL = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/

/**
 * Convierte el valor de un campo datetime-local («2026-11-20T07:58»), que se lee como hora de
 * Colombia, a ISO 8601 con zona («2026-11-20T07:58:00-05:00»). Devuelve null si no es una fecha real.
 */
export function aIsoColombia(valorLocal: string): string | null {
  const partes = PATRON_LOCAL.exec(valorLocal.trim())
  if (!partes) return null
  const [anio, mes, dia, hora, minuto] = partes.slice(1).map(Number) as [number, number, number, number, number]
  const fecha = new Date(Date.UTC(anio, mes - 1, dia, hora, minuto))
  const real =
    fecha.getUTCFullYear() === anio &&
    fecha.getUTCMonth() === mes - 1 &&
    fecha.getUTCDate() === dia &&
    fecha.getUTCHours() === hora &&
    fecha.getUTCMinutes() === minuto
  if (!real) return null
  return `${valorLocal.trim()}:00${DESFASE}`
}

/** La hora de Colombia en el formato de un campo datetime-local, por ejemplo para su atributo max. */
export function valorLocalColombia(fecha: Date = new Date()): string {
  return new Date(fecha.getTime() - DESFASE_MS).toISOString().slice(0, 16)
}

/** Una fecha como ISO 8601 con la zona de Colombia: «2026-11-20T07:58:12-05:00» (R8). */
export function isoColombia(fecha: Date = new Date()): string {
  return `${new Date(fecha.getTime() - DESFASE_MS).toISOString().slice(0, 19)}${DESFASE}`
}

/** Si la fecha ISO queda después de «ahora». */
export function esFutura(iso: string, ahora: Date = new Date()): boolean {
  return new Date(iso).getTime() > ahora.getTime()
}
