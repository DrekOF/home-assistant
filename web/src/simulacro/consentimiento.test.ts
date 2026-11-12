/**
 * Nombre: consentimiento.test.ts
 * Descripción: Pruebas de la lectura del texto del consentimiento desde specs/consentimiento.md (RF-02 · C3).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { describe, expect, it } from 'vitest'
import { extraerTextoConsentimiento, textoConsentimiento } from './consentimiento'

describe('RF-02 · C3 · texto del consentimiento', () => {
  it('RF-02 · C3 · toma la versión 1.0 y solo el texto de la autorización', () => {
    expect(textoConsentimiento.version).toBe('1.0')
    expect(textoConsentimiento.texto.startsWith('**Autorización para el tratamiento de mis datos biométricos')).toBe(true)
    expect(textoConsentimiento.texto).toContain('**No es obligatorio.**')
    expect(textoConsentimiento.texto).toContain('mi asistencia se puede registrar de forma manual')
    expect(textoConsentimiento.texto).not.toContain('Referencias')
    expect(textoConsentimiento.texto).not.toContain('Borrador para la demostración')
  })

  it('RF-02 · C3 · falla con un aviso claro si el archivo cambia de forma', () => {
    expect(() => extraerTextoConsentimiento('# Sin separadores')).toThrow('dos líneas ---')
    expect(() => extraerTextoConsentimiento('# Título\n---\nTexto\n---')).toThrow('la versión del texto')
  })
})
