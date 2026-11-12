/**
 * Nombre: fechas.test.ts
 * Descripción: Pruebas del formato de fechas en es-CO con la hora de Colombia y de la conversión a ISO 8601 (RNF-05 · C2, R8).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { describe, expect, it } from 'vitest'
import { aIsoColombia, esFutura, formatearFecha, formatearFechaHora, isoColombia, valorLocalColombia } from './fechas'

// Intl separa «a. m.» con espacios duros; para comparar, se vuelven espacios normales.
const plano = (texto: string) => texto.replace(/[\u00a0\u202f]/g, ' ')

describe('RNF-05 · C2 · fechas y horas en hora de Colombia', () => {
  it('RNF-05 · C2 · muestra la fecha y la hora en es-CO y America/Bogota', () => {
    expect(plano(formatearFechaHora('2026-11-20T12:58:12Z'))).toBe('20 de nov de 2026, 7:58 a. m.')
    expect(plano(formatearFechaHora('2026-11-20T07:58:12-05:00'))).toBe('20 de nov de 2026, 7:58 a. m.')
  })

  it('RNF-05 · C2 · une la hora y «a. m.» con espacios duros para que no se partan', () => {
    expect(formatearFechaHora('2026-11-20T12:58:12Z').endsWith('7:58\u00a0a.\u00a0m.')).toBe(true)
  })

  it('RNF-05 · C2 · usa la fecha de Colombia aunque en UTC ya sea el día siguiente', () => {
    expect(plano(formatearFechaHora('2026-11-21T03:05:00Z'))).toBe('20 de nov de 2026, 10:05 p. m.')
    expect(formatearFecha('2026-11-21T03:05:00Z')).toBe('20 de noviembre de 2026')
  })
})

describe('R8 · hora local a ISO 8601 con la zona de Colombia', () => {
  it('R8 · convierte el valor de datetime-local a ISO con -05:00', () => {
    expect(aIsoColombia('2026-11-20T07:58')).toBe('2026-11-20T07:58:00-05:00')
  })

  it('R8 · rechaza fechas que no existen o mal escritas', () => {
    expect(aIsoColombia('2026-02-30T10:00')).toBeNull()
    expect(aIsoColombia('2026-11-20T24:00')).toBeNull()
    expect(aIsoColombia('20/11/2026 07:58')).toBeNull()
    expect(aIsoColombia('')).toBeNull()
  })

  it('R8 · da la hora de Colombia para el máximo de un campo datetime-local', () => {
    expect(valorLocalColombia(new Date('2026-11-21T03:30:00Z'))).toBe('2026-11-20T22:30')
    expect(valorLocalColombia(new Date('2026-11-20T12:58:59Z'))).toBe('2026-11-20T07:58')
  })

  it('R8 · escribe una fecha como ISO 8601 con -05:00', () => {
    expect(isoColombia(new Date('2026-11-20T12:58:12Z'))).toBe('2026-11-20T07:58:12-05:00')
    expect(isoColombia(new Date('2026-11-21T03:05:00Z'))).toBe('2026-11-20T22:05:00-05:00')
  })

  it('R8 · sabe si una hora es futura', () => {
    const ahora = new Date('2026-11-20T12:00:00Z')
    expect(esFutura('2026-11-20T07:01:00-05:00', ahora)).toBe(true)
    expect(esFutura('2026-11-20T06:59:00-05:00', ahora)).toBe(false)
  })
})
