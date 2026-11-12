/**
 * Nombre: camaras.ts
 * Descripción: Textos de las cámaras (tipo y ayuda) y el campo del formulario al que corresponde un 422 del servidor (RF-10).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { TipoCamara } from '../api/cliente'
import type { CampoCamara } from './validaciones'

/** En este orden se ofrecen al crear: hoy la cámara es el simulador (D-21). */
export const TIPOS_CAMARA: TipoCamara[] = ['simulador', 'tinyml', 'respaldo']

export const NOMBRES_TIPO: Record<TipoCamara, string> = {
  simulador: 'Simulador',
  tinyml: 'TinyML',
  respaldo: 'Respaldo',
}

export const AYUDAS_TIPO: Record<TipoCamara, string> = {
  simulador: 'La webcam del portátil, con el simulador.',
  tinyml: 'Una placa que detecta la cara y envía solo el recorte.',
  respaldo: 'Una cámara que solo sirve imágenes: el servidor le pide una cada segundo a su URL de captura.',
}

/**
 * El campo del formulario que nombra el detalle de un 422 `validacion`, si nombra alguno. El esquema
 * Error no dice el campo; el servidor lo escribe en el detalle («revisa «codigo»») o en la frase de
 * la regla («El código «servidor» está reservado…», «…necesita su URL de captura.»).
 */
export function campoDe422(detalle: string): CampoCamara | undefined {
  const nombrados = new Set(Array.from(detalle.matchAll(/«([a-z_]+)»/g), (coincidencia) => coincidencia[1]))
  if (nombrados.has('codigo') || /c[oó]digo/i.test(detalle)) return 'codigo'
  if (nombrados.has('nombre')) return 'nombre'
  if (nombrados.has('url_captura') || /url de captura/i.test(detalle)) return 'url'
  return undefined
}
