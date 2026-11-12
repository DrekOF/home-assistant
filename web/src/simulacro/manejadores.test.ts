/**
 * Nombre: manejadores.test.ts
 * Descripción: Pruebas del simulacro de la API: responde como dice openapi.yaml (sesión, personas y consentimiento).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { setupServer } from 'msw/node'
import createClient from 'openapi-fetch'
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import type { paths } from '../api/esquema'
import { PATRON_DOCUMENTO } from '../logica/validaciones'
import { CREDENCIALES_SIMULACRO, crearEstado } from './datos'
import { manejadores, reiniciarSimulacro } from './manejadores'

const servidor = setupServer(...manejadores)
// fetch se busca en cada llamada: así usa el que intercepta MSW después de listen().
const api = createClient<paths>({ baseUrl: 'http://localhost', fetch: (peticion) => fetch(peticion) })

beforeAll(() => servidor.listen({ onUnhandledFrame: 'error' }))
afterAll(() => servidor.close())
beforeEach(() => reiniciarSimulacro())

async function entrar() {
  const { response } = await api.POST('/api/v1/sesion', { body: { ...CREDENCIALES_SIMULACRO } })
  expect(response.status).toBe(200)
}

async function crearPersona(documento = '1075999888') {
  const { data, response } = await api.POST('/api/v1/personas', {
    body: { documento, nombre: 'Camila Andrea Torres', rol: 'docente', horario_id: null },
  })
  expect(response.status).toBe(201)
  if (!data) throw new Error('Sin persona')
  return data
}

describe('Contrato · datos de ejemplo del simulacro', () => {
  it('Contrato · documentos válidos y únicos, y un bloque por día en cada horario (D-20)', () => {
    const estado = crearEstado()
    const documentos = estado.personas.map((p) => p.documento)
    expect(documentos.every((d) => PATRON_DOCUMENTO.test(d))).toBe(true)
    expect(new Set(documentos).size).toBe(documentos.length)
    for (const horario of estado.horarios) {
      const dias = horario.bloques.map((b) => b.dia)
      expect(new Set(dias).size).toBe(dias.length)
      expect(horario.bloques.every((b) => /^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(b.hora_inicio))).toBe(true)
    }
    // Solo tiene huellas quien tiene consentimiento vigente.
    const conVigente = new Set(estado.consentimientos.filter((c) => c.revocado_en === null).map((c) => c.persona_id))
    expect(estado.personas.filter((p) => p.muestras > 0).every((p) => conVigente.has(p.id))).toBe(true)
  })
})

describe('RNF-02 · C5 · sin sesión la API responde 401', () => {
  it('RNF-02 · C5 · pide sesión con el código sin_sesion', async () => {
    const { error, response } = await api.GET('/api/v1/personas')
    expect(response.status).toBe(401)
    expect(error).toEqual({ codigo: 'sin_sesion', detalle: 'Inicia sesión para continuar.' })
  })
})

describe('RF-09 · C1 · inicio de sesión', () => {
  it('RF-09 · C1 · rechaza credenciales que no coinciden', async () => {
    const { error, response } = await api.POST('/api/v1/sesion', {
      body: { correo: CREDENCIALES_SIMULACRO.correo, clave: 'otra-clave' },
    })
    expect(response.status).toBe(401)
    expect(error?.codigo).toBe('credenciales_invalidas')
  })

  it('RF-09 · C1 · inicia y cierra la sesión', async () => {
    await entrar()
    const { data } = await api.GET('/api/v1/sesion')
    expect(data?.correo).toBe(CREDENCIALES_SIMULACRO.correo)
    expect((await api.DELETE('/api/v1/sesion')).response.status).toBe(204)
    expect((await api.GET('/api/v1/sesion')).response.status).toBe(401)
  })
})

describe('RF-02 · C1 · personas', () => {
  beforeEach(entrar)

  it('RF-02 · C1 · busca sin tildes, filtra y pagina', async () => {
    const busqueda = await api.GET('/api/v1/personas', { params: { query: { q: 'nunez' } } })
    expect(busqueda.data?.elementos.map((p) => p.nombre)).toEqual(['Esteban Calderón Núñez'])
    const inactivas = await api.GET('/api/v1/personas', { params: { query: { activa: false } } })
    expect(inactivas.data?.elementos.every((p) => !p.activa)).toBe(true)
    const pagina = await api.GET('/api/v1/personas', { params: { query: { pagina: 3, por_pagina: 5 } } })
    expect(pagina.data).toMatchObject({ total: 12, pagina: 3, por_pagina: 5 })
    expect(pagina.data?.elementos).toHaveLength(2)
  })

  it('RF-02 · C1 · crea, edita, desactiva y no repite documentos', async () => {
    const persona = await crearPersona()
    expect(persona).toMatchObject({ activa: true, consentimiento_vigente: false, muestras: 0, horario_nombre: null })
    const duplicada = await api.POST('/api/v1/personas', { body: { documento: '1075999888', nombre: 'Otra' } })
    expect(duplicada.response.status).toBe(409)
    expect(duplicada.error?.codigo).toBe('documento_duplicado')
    const invalida = await api.POST('/api/v1/personas', { body: { documento: '1.075', nombre: 'Otra' } })
    expect(invalida.response.status).toBe(422)
    expect(invalida.error?.codigo).toBe('validacion')
    const editada = await api.PATCH('/api/v1/personas/{persona_id}', {
      params: { path: { persona_id: persona.id } },
      body: { activa: false, nombre: 'Camila Torres' },
    })
    expect(editada.data).toMatchObject({ activa: false, nombre: 'Camila Torres' })
  })

  it('RF-02 · C1 · responde 404 con el esquema Error si la persona no existe', async () => {
    const { error, response } = await api.GET('/api/v1/personas/{persona_id}', {
      params: { path: { persona_id: '00000000-0000-4000-8000-999999999999' } },
    })
    expect(response.status).toBe(404)
    expect(error?.codigo).toBe('no_encontrado')
  })
})

describe('RF-02 · C2 y C5 · consentimiento', () => {
  beforeEach(entrar)

  it('RF-02 · C2 · responde null sin consentimiento vigente y exige la versión vigente del texto', async () => {
    const persona = await crearPersona()
    const ruta = { params: { path: { persona_id: persona.id } } }
    const sinConsentimiento = await api.GET('/api/v1/personas/{persona_id}/consentimiento', ruta)
    expect(sinConsentimiento.response.status).toBe(200)
    expect(sinConsentimiento.data).toBeNull()
    const vieja = await api.POST('/api/v1/personas/{persona_id}/consentimiento', {
      ...ruta,
      body: { version_texto: '0.9', acepta: true },
    })
    expect(vieja.response.status).toBe(422)
    expect(vieja.error?.codigo).toBe('version_texto_invalida')
  })

  it('RF-02 · C2 · registra el consentimiento en papel con la fecha de la firma, una sola vez', async () => {
    const persona = await crearPersona()
    const ruta = { params: { path: { persona_id: persona.id } } }
    const texto = await api.GET('/api/v1/consentimiento/texto')
    const cuerpo = { version_texto: texto.data?.version ?? '', acepta: true as const, medio: 'papel' as const, aceptado_en: '2026-11-10T16:45:00-05:00' }
    const registrado = await api.POST('/api/v1/personas/{persona_id}/consentimiento', { ...ruta, body: cuerpo })
    expect(registrado.response.status).toBe(201)
    expect(registrado.data).toMatchObject({ medio: 'papel', aceptado_en: '2026-11-10T16:45:00-05:00', version_texto: '1.0' })
    const otraVez = await api.POST('/api/v1/personas/{persona_id}/consentimiento', { ...ruta, body: cuerpo })
    expect(otraVez.response.status).toBe(409)
    expect(otraVez.error?.codigo).toBe('consentimiento_vigente')
    const ficha = await api.GET('/api/v1/personas/{persona_id}', ruta)
    expect(ficha.data?.consentimiento_vigente).toBe(true)
  })

  it('RF-02 · C5 · revocar borra las huellas y deja el consentimiento en el historial', async () => {
    const anaId = '00000000-0000-4000-8000-000000000001'
    const ruta = { params: { path: { persona_id: anaId } } }
    expect((await api.GET('/api/v1/personas/{persona_id}', ruta)).data?.muestras).toBe(5)
    expect((await api.DELETE('/api/v1/personas/{persona_id}/consentimiento', ruta)).response.status).toBe(204)
    const ficha = await api.GET('/api/v1/personas/{persona_id}', ruta)
    expect(ficha.data).toMatchObject({ muestras: 0, consentimiento_vigente: false })
    expect((await api.GET('/api/v1/personas/{persona_id}/consentimiento', ruta)).data).toBeNull()
    const historial = await api.GET('/api/v1/personas/{persona_id}/consentimientos', ruta)
    expect(historial.data).toHaveLength(1)
    expect(historial.data?.[0]?.revocado_en).toMatch(/-05:00$/)
    const otraVez = await api.DELETE('/api/v1/personas/{persona_id}/consentimiento', ruta)
    expect(otraVez.response.status).toBe(404)
  })
})
