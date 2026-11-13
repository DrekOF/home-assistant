/**
 * Nombre: inscripcion.test.ts
 * Descripción: Pruebas de los textos de cada motivo de rechazo (RF-03 · C6, R7) y del tiempo que falta hasta que vence la inscripción (R9).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { contarMuestras, formatearRestante, MOTIVOS, restanteHasta, textoConservadas } from './inscripcion'

// Los valores de MotivoMuestra, leídos del contrato: si el contrato suma uno, esta prueba avisa.
const contrato = readFileSync(new URL('../../../specs/contratos/openapi.yaml', import.meta.url), 'utf8')
const motivosDelContrato = /MotivoMuestra:\s*\n\s*type: string\s*\n\s*enum: \[([^\]]+)\]/.exec(contrato)?.[1]

describe('RF-03 · C6 · el motivo del último rechazo en español', () => {
  it('RF-03 · C6 · hay un texto por cada valor de MotivoMuestra del contrato', () => {
    const valores = (motivosDelContrato ?? '').split(',').map((valor) => valor.trim())
    expect(valores.length).toBeGreaterThan(0)
    expect(Object.keys(MOTIVOS).sort()).toEqual([...valores].sort())
  })

  it('RF-03 · C6 · cada motivo dice qué pasó y qué hacer, en frases completas', () => {
    for (const { que, hacer } of Object.values(MOTIVOS)) {
      expect(que).toMatch(/^[A-ZÁÉÍÓÚÑ].+\.$/)
      expect(hacer).toMatch(/^[A-ZÁÉÍÓÚÑ¿].+\.$/)
    }
    expect(MOTIVOS.cara_pequena.hacer).toBe('Acércate a la cámara.')
  })

  it('RNF-01 · C3 · parece_otra_persona no dice a quién se parece', () => {
    const { que, hacer } = MOTIVOS.parece_otra_persona
    expect(`${que} ${hacer}`).not.toMatch(/«|»|:/)
  })
})

describe('R9 · el tiempo que falta hasta que vence', () => {
  const vence = '2026-11-12T16:02:00-05:00'
  const ahora = Date.parse('2026-11-12T16:00:18-05:00')

  it('R9 · cuenta los milisegundos hasta vence', () => {
    expect(restanteHasta(vence, ahora)).toBe(102_000)
    expect(restanteHasta(vence, Date.parse(vence) + 5000)).toBe(-5000)
  })

  it('R9 · lo muestra en minutos y segundos, sin bajar de 0:00', () => {
    expect(formatearRestante(102_000)).toBe('1:42')
    expect(formatearRestante(120_000)).toBe('2:00')
    expect(formatearRestante(9000)).toBe('0:09')
    expect(formatearRestante(-5000)).toBe('0:00')
  })

  it('R9 · redondea hacia arriba: con medio segundo por delante todavía no es 0:00', () => {
    expect(formatearRestante(500)).toBe('0:01')
    expect(formatearRestante(59_001)).toBe('1:00')
  })

  it('RF-03 · C6 · cuenta las muestras en singular y plural', () => {
    expect(contarMuestras(1)).toBe('1 muestra')
    expect(contarMuestras(0)).toBe('0 muestras')
    expect(contarMuestras(5)).toBe('5 muestras')
  })

  it('RF-03 · C4 · dice qué muestras se conservan, sin «las 0 muestras»', () => {
    expect(textoConservadas(0)).toBe('No hay muestras aceptadas.')
    expect(textoConservadas(1)).toBe('La muestra aceptada se conserva.')
    expect(textoConservadas(3)).toBe('Las 3 muestras aceptadas se conservan.')
  })
})
