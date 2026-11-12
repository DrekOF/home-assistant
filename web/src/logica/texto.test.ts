/**
 * Nombre: texto.test.ts
 * Descripción: Pruebas de la búsqueda sin tildes y de la lectura del Markdown del consentimiento (RF-02 · C1 y C3).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { describe, expect, it } from 'vitest'
import { coincide, leerParrafos, normalizar } from './texto'

describe('RF-02 · C1 · búsqueda sin importar tildes ni mayúsculas', () => {
  it('RF-02 · C1 · quita tildes y mayúsculas', () => {
    expect(normalizar('  Óscar Iván NÚÑEZ ')).toBe('oscar ivan nunez')
  })

  it('RF-02 · C1 · encuentra por nombre o documento', () => {
    expect(coincide('nunez', 'Esteban Calderón Núñez', '1075000012')).toBe(true)
    expect(coincide('OSCAR', 'Óscar Iván Cabrera', '93123456')).toBe(true)
    expect(coincide('9312', 'Óscar Iván Cabrera', '93123456')).toBe(true)
    expect(coincide('maría', 'Ana Gómez', '1075234567')).toBe(false)
    expect(coincide('   ', 'Ana Gómez')).toBe(true)
  })
})

describe('RF-02 · C3 · texto del consentimiento', () => {
  it('RF-02 · C3 · separa párrafos y negritas sin interpretar HTML', () => {
    const md = '**No es obligatorio.** No estoy obligado.\nSigue aquí.\n\nSegundo <b>párrafo</b>.'
    expect(leerParrafos(md)).toEqual([
      [
        { negrita: true, texto: 'No es obligatorio.' },
        { negrita: false, texto: ' No estoy obligado. Sigue aquí.' },
      ],
      [{ negrita: false, texto: 'Segundo <b>párrafo</b>.' }],
    ])
  })
})
