/**
 * Nombre: consentimiento.ts
 * Descripción: Texto del consentimiento para el simulacro, leído de specs/consentimiento.md como lo hará el servidor.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import markdown from '../../../specs/consentimiento.md?raw'
import type { TextoConsentimiento } from '../api/cliente'

/**
 * El texto es el bloque entre las dos líneas «---» de consentimiento.md, y la versión sale de su
 * título («versión del texto 1.0»).
 */
export function extraerTextoConsentimiento(md: string): TextoConsentimiento {
  const lineas = md.replace(/\r\n/g, '\n').split('\n')
  const inicio = lineas.indexOf('---')
  const fin = lineas.indexOf('---', inicio + 1)
  if (inicio < 0 || fin < 0) throw new Error('consentimiento.md no tiene el texto entre dos líneas ---')
  const version = /versión del texto (\d+(?:\.\d+)*)/.exec(md)?.[1]
  if (!version) throw new Error('consentimiento.md no dice la versión del texto en su título')
  return { version, texto: lineas.slice(inicio + 1, fin).join('\n').trim() }
}

export const textoConsentimiento = extraerTextoConsentimiento(markdown)
