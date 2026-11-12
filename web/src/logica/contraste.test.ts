/**
 * Nombre: contraste.test.ts
 * Descripción: Prueba el contraste AA (WCAG 2.2) de los pares de colores de tokens.css que se usan en pantalla.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const css = readFileSync(fileURLToPath(new URL('../estilos/tokens.css', import.meta.url)), 'utf8')
const tokens = new Map([...css.matchAll(/--(color-[a-z0-9-]+):\s*(#[0-9a-f]{6});/gi)].map((m) => [m[1], m[2]]))

function color(nombre: string): string {
  const valor = tokens.get(nombre)
  if (!valor) throw new Error(`tokens.css no tiene --${nombre}`)
  return valor
}

/** Luminancia relativa de WCAG. */
function luminancia(hex: string): number {
  const n = Number.parseInt(hex.slice(1), 16)
  const canal = (c: number) => {
    const s = c / 255
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * canal((n >> 16) & 255) + 0.7152 * canal((n >> 8) & 255) + 0.0722 * canal(n & 255)
}

function contraste(primero: string, segundo: string): number {
  const [claro, oscuro] = [luminancia(color(primero)), luminancia(color(segundo))].sort((a, b) => b - a) as [number, number]
  return (claro + 0.05) / (oscuro + 0.05)
}

// [texto, fondo]: cada par que aparece en la web.
const TEXTO: Array<[string, string]> = [
  ['color-texto', 'color-fondo'],
  ['color-texto', 'color-superficie'],
  ['color-texto', 'color-lateral'],
  ['color-texto', 'color-acento-suave'],
  ['color-texto', 'color-aviso-fondo'],
  ['color-texto', 'color-ok-fondo'],
  ['color-texto', 'color-error-fondo'],
  ['color-texto-2', 'color-fondo'],
  ['color-texto-2', 'color-superficie'],
  ['color-texto-2', 'color-lateral'],
  ['color-texto-2', 'color-neutro-fondo'],
  ['color-marcador', 'color-superficie'],
  ['color-acento', 'color-superficie'],
  ['color-acento', 'color-fondo'],
  ['color-acento', 'color-lateral'],
  ['color-acento', 'color-acento-suave'],
  ['color-sobre-acento', 'color-acento'],
  ['color-sobre-acento', 'color-acento-oscuro'],
  ['color-sobre-acento-2', 'color-acento'],
  ['color-sobre-acento', 'color-error'],
  ['color-sobre-acento', 'color-error-oscuro'],
  ['color-error', 'color-superficie'],
  ['color-error', 'color-error-fondo'],
  ['color-ok', 'color-ok-fondo'],
  ['color-aviso', 'color-aviso-fondo'],
  ['color-neutro', 'color-neutro-fondo'],
]

// Bordes de controles y anillo de foco: 3:1 contra lo que tienen al lado (WCAG 1.4.11).
const CONTROLES: Array<[string, string]> = [
  ['color-borde', 'color-superficie'],
  ['color-borde', 'color-fondo'],
  ['color-acento', 'color-fondo'],
  ['color-acento', 'color-lateral'],
  ['color-error', 'color-superficie'],
]

describe('Accesibilidad · contraste AA de los colores (tarea C)', () => {
  it.each(TEXTO)('Accesibilidad · AA · %s sobre %s llega a 4,5:1', (texto, fondo) => {
    expect(contraste(texto, fondo)).toBeGreaterThanOrEqual(4.5)
  })

  it.each(CONTROLES)('Accesibilidad · AA · %s junto a %s llega a 3:1', (borde, fondo) => {
    expect(contraste(borde, fondo)).toBeGreaterThanOrEqual(3)
  })
})
