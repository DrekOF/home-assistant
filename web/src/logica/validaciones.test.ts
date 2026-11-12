/**
 * Nombre: validaciones.test.ts
 * Descripción: Pruebas de las validaciones de inicio de sesión, persona y consentimiento (RF-09 · C1, RF-02 · C1 y C2).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { describe, expect, it } from 'vitest'
import { hayErrores, limpiarNombre, validarConsentimiento, validarCredenciales, validarPersona } from './validaciones'

describe('RF-09 · C1 · inicio de sesión', () => {
  it('RF-09 · C1 · pide correo válido y clave de al menos 8 caracteres', () => {
    expect(validarCredenciales({ correo: '', clave: '' })).toEqual({
      correo: 'Escribe tu correo.',
      clave: 'Escribe tu clave.',
    })
    expect(validarCredenciales({ correo: 'admin', clave: 'corta' })).toEqual({
      correo: 'Escribe un correo válido, como nombre@dominio.co.',
      clave: 'La clave tiene al menos 8 caracteres.',
    })
    expect(validarCredenciales({ correo: ' admin@example.com ', clave: 'simulacro' })).toEqual({})
  })
})

describe('RF-02 · C1 · datos de la persona', () => {
  it('RF-02 · C1 · acepta nombre y documento como los pide el contrato', () => {
    expect(validarPersona({ nombre: 'Ana María Gómez', documento: '1075234567' })).toEqual({})
    expect(validarPersona({ nombre: 'Ana', documento: 'CE-12345' })).toEqual({})
  })

  it('RF-02 · C1 · pide nombre de 2 a 120 caracteres', () => {
    expect(validarPersona({ nombre: '   ', documento: '123' }).nombre).toBe('Escribe el nombre completo.')
    expect(validarPersona({ nombre: 'A', documento: '123' }).nombre).toBe('El nombre necesita al menos 2 letras.')
    expect(validarPersona({ nombre: 'a'.repeat(121), documento: '123' }).nombre).toBe(
      'El nombre puede tener hasta 120 caracteres.',
    )
  })

  it('RF-02 · C1 · pide un documento de 3 a 20 letras, números o guiones', () => {
    const mensaje = 'Usa de 3 a 20 letras, números o guiones, sin espacios ni puntos.'
    expect(validarPersona({ nombre: 'Ana', documento: '' }).documento).toBe('Escribe el número de documento.')
    expect(validarPersona({ nombre: 'Ana', documento: '12' }).documento).toBe(mensaje)
    expect(validarPersona({ nombre: 'Ana', documento: '1.075.234' }).documento).toBe(mensaje)
    expect(validarPersona({ nombre: 'Ana', documento: '1075 234' }).documento).toBe(mensaje)
    expect(validarPersona({ nombre: 'Ana', documento: '1'.repeat(21) }).documento).toBe(mensaje)
  })

  it('RF-02 · C1 · limpia los espacios del nombre', () => {
    expect(limpiarNombre('  Ana   María  Gómez ')).toBe('Ana María Gómez')
  })
})

describe('RF-02 · C2 · registro del consentimiento', () => {
  const ahora = new Date('2026-11-20T12:00:00Z') // 07:00 en Colombia

  it('RF-02 · C2 · exige que la persona acepte', () => {
    expect(validarConsentimiento({ medio: 'web', acepta: false, aceptadoEn: '' }, ahora)).toEqual({
      acepta: 'Marca la casilla solo cuando la persona haya aceptado.',
    })
    expect(validarConsentimiento({ medio: 'web', acepta: true, aceptadoEn: '' }, ahora)).toEqual({})
  })

  it('RF-02 · C2 · con papel pide la fecha de la firma, que no puede ser futura', () => {
    expect(validarConsentimiento({ medio: 'papel', acepta: true, aceptadoEn: '' }, ahora).aceptadoEn).toBe(
      'Escribe la fecha y la hora en que la persona firmó.',
    )
    expect(
      validarConsentimiento({ medio: 'papel', acepta: true, aceptadoEn: '2026-11-20T07:30' }, ahora).aceptadoEn,
    ).toBe('La fecha de la firma no puede ser futura.')
    expect(
      validarConsentimiento({ medio: 'papel', acepta: true, aceptadoEn: '2026-02-30T07:30' }, ahora).aceptadoEn,
    ).toBe('Escribe una fecha y una hora válidas.')
    expect(validarConsentimiento({ medio: 'papel', acepta: true, aceptadoEn: '2026-11-19T16:45' }, ahora)).toEqual({})
  })

  it('RF-02 · C2 · sabe si quedan errores', () => {
    expect(hayErrores({})).toBe(false)
    expect(hayErrores({ acepta: undefined })).toBe(false)
    expect(hayErrores({ acepta: 'Falta' })).toBe(true)
  })
})
