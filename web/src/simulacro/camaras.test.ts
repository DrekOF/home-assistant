/**
 * Nombre: camaras.test.ts
 * Descripción: Pruebas del simulacro de cámaras: responde como dice openapi.yaml (RF-10 · C1 a C3), con el token una sola vez.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { setupServer } from 'msw/node'
import createClient from 'openapi-fetch'
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import type { paths } from '../api/esquema'
import { PATRON_CODIGO_CAMARA } from '../logica/validaciones'
import { CREDENCIALES_SIMULACRO, crearEstado } from './datos'
import { manejadores, reiniciarSimulacro } from './manejadores'

const servidor = setupServer(...manejadores)
const api = createClient<paths>({ baseUrl: 'http://localhost', fetch: (peticion) => fetch(peticion) })

beforeAll(() => servidor.listen({ onUnhandledFrame: 'error' }))
afterAll(() => servidor.close())
beforeEach(async () => {
  reiniciarSimulacro()
  const { response } = await api.POST('/api/v1/sesion', { body: { ...CREDENCIALES_SIMULACRO } })
  expect(response.status).toBe(200)
})

const ruta = (codigo: string) => ({ params: { path: { codigo } } })
const PATRON_TOKEN = /^[A-Za-z0-9_-]{43}$/

describe('Contrato · cámaras de ejemplo del simulacro', () => {
  it('Contrato · códigos válidos y únicos, y las de respaldo con su URL de captura', () => {
    const { camaras } = crearEstado()
    expect(camaras.every((c) => PATRON_CODIGO_CAMARA.test(c.codigo))).toBe(true)
    expect(new Set(camaras.map((c) => c.codigo)).size).toBe(camaras.length)
    expect(camaras.filter((c) => c.tipo === 'respaldo').every((c) => c.url_captura !== null)).toBe(true)
  })
})

describe('RF-10 · C3 · lista de cámaras', () => {
  it('RF-10 · C3 · lista por código, con en línea, último contacto y modo', async () => {
    const { data, response } = await api.GET('/api/v1/dispositivos')
    expect(response.status).toBe(200)
    expect(data?.map((c) => c.codigo)).toEqual(['entrada', 'patio', 'salida'])
    const [entrada, , salida] = data ?? []
    expect(entrada).toMatchObject({ tipo: 'simulador', activo: true, en_linea: true, modo: 'reconocer', inscripcion_activa: null })
    expect(entrada?.ultimo_contacto).toMatch(/-05:00$/)
    expect(salida).toMatchObject({ en_linea: false, ultimo_contacto: '2026-11-11T18:42:00-05:00' })
    // El token nunca sale en la lista.
    expect(data?.some((c) => 'token' in c)).toBe(false)
  })

  it('RF-10 · C3 · pide sesión y responde 404 con el esquema Error si la cámara no existe', async () => {
    const noExiste = await api.GET('/api/v1/dispositivos/{codigo}', ruta('no-existe'))
    expect(noExiste.response.status).toBe(404)
    expect(noExiste.error?.codigo).toBe('no_encontrado')
    await api.DELETE('/api/v1/sesion')
    const sinSesion = await api.GET('/api/v1/dispositivos')
    expect(sinSesion.response.status).toBe(401)
    expect(sinSesion.error?.codigo).toBe('sin_sesion')
  })
})

describe('RF-10 · C1 · crear una cámara', () => {
  it('RF-10 · C1 · la crea y da su token una sola vez', async () => {
    const creada = await api.POST('/api/v1/dispositivos', { body: { codigo: 'porteria', nombre: 'Portería', tipo: 'tinyml' } })
    expect(creada.response.status).toBe(201)
    expect(creada.data).toMatchObject({ codigo: 'porteria', activo: true, en_linea: false, modo: 'reconocer', url_captura: null })
    expect(creada.data?.token).toMatch(PATRON_TOKEN)
    const vista = await api.GET('/api/v1/dispositivos/{codigo}', ruta('porteria'))
    expect(vista.data?.nombre).toBe('Portería')
    expect(vista.data && 'token' in vista.data).toBe(false)
  })

  it('RF-10 · C1 · rechaza el código servidor, un código mal escrito y un respaldo sin URL (422)', async () => {
    const reservado = await api.POST('/api/v1/dispositivos', { body: { codigo: 'servidor', nombre: 'Servidor', tipo: 'tinyml' } })
    expect(reservado.response.status).toBe(422)
    expect(reservado.error).toEqual({
      codigo: 'validacion',
      detalle: 'Los datos no son válidos. El código «servidor» está reservado para los temas MQTT del servidor.',
    })
    const malEscrito = await api.POST('/api/v1/dispositivos', { body: { codigo: 'Entrada 2', nombre: 'X', tipo: 'tinyml' } })
    expect(malEscrito.response.status).toBe(422)
    expect(malEscrito.error?.detalle).toBe('Los datos no son válidos: revisa «codigo», «nombre».')
    const sinUrl = await api.POST('/api/v1/dispositivos', { body: { codigo: 'patio-2', nombre: 'Patio 2', tipo: 'respaldo' } })
    expect(sinUrl.response.status).toBe(422)
    expect(sinUrl.error?.detalle).toContain('necesita su URL de captura')
  })

  it('RF-10 · C1 · no repite códigos (409 codigo_duplicado)', async () => {
    const repetida = await api.POST('/api/v1/dispositivos', { body: { codigo: 'entrada', nombre: 'Otra', tipo: 'simulador' } })
    expect(repetida.response.status).toBe(409)
    expect(repetida.error).toEqual({ codigo: 'codigo_duplicado', detalle: 'Ya hay una cámara con el código entrada.' })
  })
})

describe('RF-10 · C2 · token y cambios', () => {
  it('RF-10 · C2 · cambia el token: cada vez uno nuevo', async () => {
    const primero = await api.POST('/api/v1/dispositivos/{codigo}/token', ruta('entrada'))
    const segundo = await api.POST('/api/v1/dispositivos/{codigo}/token', ruta('entrada'))
    expect(primero.response.status).toBe(200)
    expect(primero.data?.token).toMatch(PATRON_TOKEN)
    expect(segundo.data?.token).not.toBe(primero.data?.token)
    const noExiste = await api.POST('/api/v1/dispositivos/{codigo}/token', ruta('no-existe'))
    expect(noExiste.response.status).toBe(404)
  })

  it('RF-10 · C1 · edita nombre, tipo, URL y si está activa', async () => {
    const editada = await api.PATCH('/api/v1/dispositivos/{codigo}', {
      ...ruta('salida'),
      body: { nombre: 'Salida norte', tipo: 'respaldo', url_captura: 'http://192.168.137.60/capture', activo: false },
    })
    expect(editada.response.status).toBe(200)
    expect(editada.data).toMatchObject({ nombre: 'Salida norte', tipo: 'respaldo', activo: false })
    const sinUrl = await api.PATCH('/api/v1/dispositivos/{codigo}', { ...ruta('salida'), body: { url_captura: null } })
    expect(sinUrl.response.status).toBe(422)
    expect(sinUrl.error?.detalle).toBe('Una cámara de respaldo necesita su URL de captura.')
    const vacio = await api.PATCH('/api/v1/dispositivos/{codigo}', { ...ruta('salida'), body: {} })
    expect(vacio.response.status).toBe(422)
    const noExiste = await api.PATCH('/api/v1/dispositivos/{codigo}', { ...ruta('no-existe'), body: { activo: true } })
    expect(noExiste.response.status).toBe(404)
  })
})
