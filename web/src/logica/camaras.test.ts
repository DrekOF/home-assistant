/**
 * Nombre: camaras.test.ts
 * Descripción: Pruebas de la validación del formulario de cámaras (RF-10 · C1) y del campo al que va un 422 del servidor.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { describe, expect, it } from 'vitest'
import { campoDe422, NOMBRES_TIPO, TIPOS_CAMARA } from './camaras'
import { esUrlCaptura, validarCamara } from './validaciones'

const bien = { codigo: 'entrada', nombre: 'Entrada', tipo: 'simulador' as const, url: '' }

describe('RF-10 · C1 · el código de la cámara', () => {
  it('RF-10 · C1 · acepta de 3 a 32 minúsculas, números o guiones', () => {
    expect(validarCamara(bien)).toEqual({})
    expect(validarCamara({ ...bien, codigo: 'sal-2' })).toEqual({})
    expect(validarCamara({ ...bien, codigo: 'a'.repeat(32) })).toEqual({})
  })

  it('RF-10 · C1 · rechaza mayúsculas, espacios, tildes y largos fuera de rango', () => {
    const mensaje = 'Usa de 3 a 32 letras minúsculas, números o guiones, sin espacios ni tildes.'
    for (const codigo of ['Entrada', 'sala 2', 'patío', 'ab', 'a'.repeat(33), 'sal_2']) {
      expect(validarCamara({ ...bien, codigo }).codigo).toBe(mensaje)
    }
    expect(validarCamara({ ...bien, codigo: '  ' }).codigo).toBe('Escribe el código de la cámara.')
  })

  it('RF-10 · C1 · el código servidor está reservado', () => {
    expect(validarCamara({ ...bien, codigo: 'servidor' }).codigo).toBe(
      '«servidor» está reservado para el servidor. Elige otro código.',
    )
  })

  it('RF-10 · C1 · al editar no revisa el código, que ya no cambia', () => {
    expect(validarCamara({ nombre: 'Entrada', tipo: 'tinyml', url: '' })).toEqual({})
  })
})

describe('RF-10 · C1 · nombre, tipo y URL de captura', () => {
  it('RF-10 · C1 · pide un nombre de 2 a 60 caracteres', () => {
    expect(validarCamara({ ...bien, nombre: ' ' }).nombre).toBe('Escribe el nombre de la cámara.')
    expect(validarCamara({ ...bien, nombre: 'E' }).nombre).toBe('El nombre necesita al menos 2 letras.')
    expect(validarCamara({ ...bien, nombre: 'e'.repeat(61) }).nombre).toBe('El nombre puede tener hasta 60 caracteres.')
  })

  it('RF-10 · C4 · la URL de captura es obligatoria solo para una cámara de respaldo', () => {
    expect(validarCamara({ ...bien, tipo: 'respaldo' }).url).toBe('Una cámara de respaldo necesita su URL de captura.')
    expect(validarCamara({ ...bien, tipo: 'respaldo', url: 'http://192.168.137.50/capture' })).toEqual({})
    expect(validarCamara({ ...bien, tipo: 'tinyml', url: '' })).toEqual({})
  })

  it('RF-10 · C4 · la URL tiene que ser completa, con http o https', () => {
    expect(esUrlCaptura('http://192.168.137.50/capture')).toBe(true)
    expect(esUrlCaptura('https://camara.local/capture')).toBe(true)
    for (const url of ['192.168.137.50/capture', 'ftp://camara/capture', 'http://', 'captura']) {
      expect(esUrlCaptura(url)).toBe(false)
    }
    expect(validarCamara({ ...bien, url: 'camara/capture' }).url).toBe(
      'Escribe una dirección completa, como http://192.168.137.50/capture.',
    )
  })

  it('RF-10 · C1 · los tres tipos del contrato tienen nombre', () => {
    expect([...TIPOS_CAMARA].sort()).toEqual(['respaldo', 'simulador', 'tinyml'])
    expect(TIPOS_CAMARA.map((tipo) => NOMBRES_TIPO[tipo])).toEqual(['Simulador', 'TinyML', 'Respaldo'])
  })
})

describe('RF-10 · C1 · un 422 del servidor va junto al campo que falló', () => {
  it('RF-10 · C1 · toma el campo que nombra el detalle', () => {
    expect(campoDe422('Los datos no son válidos: revisa «codigo».')).toBe('codigo')
    expect(campoDe422('Los datos no son válidos: revisa «nombre».')).toBe('nombre')
    expect(campoDe422('Los datos no son válidos: revisa «url_captura».')).toBe('url')
    expect(campoDe422('Los datos no son válidos. El código «servidor» está reservado para los temas MQTT del servidor.')).toBe(
      'codigo',
    )
    expect(campoDe422('Una cámara de respaldo necesita su URL de captura.')).toBe('url')
  })

  it('RF-10 · C1 · si no nombra un campo, no adivina', () => {
    expect(campoDe422('Revisa el cuerpo de la petición.')).toBeUndefined()
  })
})
