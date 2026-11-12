/**
 * Nombre: horarios.test.ts
 * Descripción: Pruebas del resumen de los bloques de un horario (RF-13 · C1, D-20).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { describe, expect, it } from 'vitest'
import { resumirBloques } from './horarios'

const bloque = (dia: number, hora_inicio = '07:00', tolerancia_min = 10) => ({ dia, hora_inicio, tolerancia_min })

// «10 min» lleva espacio duro; para comparar, se vuelve un espacio normal.
const resumir = (bloques: Parameters<typeof resumirBloques>[0]) => resumirBloques(bloques).replace(/\u00a0/g, ' ')

describe('RF-13 · C1 · resumen de los bloques de un horario', () => {
  it('RF-13 · C1 · une el número y «min» con un espacio duro', () => {
    expect(resumirBloques([bloque(1)])).toBe('Lun, 07:00, tolerancia de 10\u00a0min')
  })

  it('RF-13 · C1 · agrupa los días seguidos con la misma hora', () => {
    expect(resumir([1, 2, 3, 4, 5].map((dia) => bloque(dia)))).toBe('Lun a vie, 07:00, tolerancia de 10 min')
    expect(resumir([1, 2, 3, 4, 5, 6, 7].map((dia) => bloque(dia)))).toBe(
      'Lun a dom, 07:00, tolerancia de 10 min',
    )
  })

  it('RF-13 · C1 · separa los días con horas distintas (D-20)', () => {
    expect(resumir([bloque(1, '07:00', 10), bloque(3, '18:00', 15)])).toBe(
      'Lun, 07:00, tolerancia de 10 min; mié, 18:00, tolerancia de 15 min',
    )
  })

  it('RF-13 · C1 · escribe como rango solo tres o más días seguidos', () => {
    expect(resumir([1, 2, 4].map((dia) => bloque(dia)))).toBe('Lun, mar y jue, 07:00, tolerancia de 10 min')
    expect(resumir([1, 2, 3, 5].map((dia) => bloque(dia)))).toBe('Lun a mié y vie, 07:00, tolerancia de 10 min')
  })

  it('RF-13 · C1 · ordena por día aunque los bloques lleguen desordenados', () => {
    expect(resumir([bloque(5), bloque(1), bloque(3), bloque(2), bloque(4)])).toBe(
      'Lun a vie, 07:00, tolerancia de 10 min',
    )
  })

  it('RF-13 · C1 · dice cuando no hay tolerancia', () => {
    expect(resumir([bloque(6, '08:00', 0)])).toBe('Sáb, 08:00, sin tolerancia')
  })
})
