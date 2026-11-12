/**
 * Nombre: inscripciones.test.ts
 * Descripción: Pruebas del simulacro de inscripciones: responde como dice openapi.yaml y sigue R9 (RF-03 · C1 a C6), con el reloj de Vitest.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { setupServer } from 'msw/node'
import createClient from 'openapi-fetch'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import type { paths } from '../api/esquema'
import { CREDENCIALES_SIMULACRO, PASO_MS, VENCE_MS } from './datos'
import { manejadores, reiniciarSimulacro } from './manejadores'

const servidor = setupServer(...manejadores)
const api = createClient<paths>({ baseUrl: 'http://localhost', fetch: (peticion) => fetch(peticion) })

// Personas de los datos de ejemplo: Ana tiene consentimiento vigente y 5 muestras; Laura no tiene consentimiento.
const ANA = '00000000-0000-4000-8000-000000000001'
const CARLOS = '00000000-0000-4000-8000-000000000002'
const LAURA = '00000000-0000-4000-8000-000000000003'
const INICIO = new Date('2026-11-12T16:00:00-05:00')

beforeAll(() => servidor.listen({ onUnhandledFrame: 'error' }))
afterAll(() => servidor.close())
beforeEach(async () => {
  // Solo el reloj de Date: los temporizadores de MSW siguen siendo los reales.
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(INICIO)
  reiniciarSimulacro()
  const { response } = await api.POST('/api/v1/sesion', { body: { ...CREDENCIALES_SIMULACRO } })
  expect(response.status).toBe(200)
})
afterEach(() => vi.useRealTimers())

const pasar = (milisegundos: number) => vi.setSystemTime(Date.now() + milisegundos)
const rutaInscripcion = (id: string) => ({ params: { path: { inscripcion_id: id } } })

async function abrir(persona_id: string, dispositivo = 'entrada') {
  return api.POST('/api/v1/inscripciones', { body: { persona_id, dispositivo } })
}

async function abrirBien(persona_id: string, dispositivo = 'entrada') {
  const { data, response } = await abrir(persona_id, dispositivo)
  expect(response.status).toBe(201)
  if (!data) throw new Error('Sin inscripción')
  return data
}

async function ver(id: string) {
  const { data } = await api.GET('/api/v1/inscripciones/{inscripcion_id}', rutaInscripcion(id))
  if (!data) throw new Error('Sin inscripción')
  return data
}

describe('RF-03 · C1 · abrir una inscripción', () => {
  it('RF-03 · C1 · la abre activa, con 5 requeridas y que vence a los 120 s', async () => {
    const inscripcion = await abrirBien(ANA)
    expect(inscripcion).toMatchObject({
      persona: { id: ANA, nombre: 'Ana María Gómez Rojas' },
      dispositivo: 'entrada',
      estado: 'activa',
      muestras: 0,
      requeridas: 5,
      ultimo_motivo: null,
      terminada: null,
    })
    expect(Date.parse(inscripcion.vence) - Date.parse(inscripcion.creada)).toBe(VENCE_MS)
    expect(inscripcion.creada).toMatch(/-05:00$/)
  })

  it('RF-03 · C5 · la cámara muestra la inscripción activa y el modo inscribir', async () => {
    const inscripcion = await abrirBien(ANA)
    const { data } = await api.GET('/api/v1/dispositivos/{codigo}', { params: { path: { codigo: 'entrada' } } })
    expect(data).toMatchObject({
      modo: 'inscribir',
      inscripcion_activa: { id: inscripcion.id, muestras: 0, requeridas: 5, estado: 'activa', vence: inscripcion.vence },
    })
  })

  it('R9 · revisa en orden: persona, cámara, cámara activa y consentimiento', async () => {
    const noExiste = '00000000-0000-4000-8000-999999999999'
    expect((await abrir(noExiste, 'no-existe')).error?.detalle).toBe('Esa persona no existe o ya fue borrada.')
    const sinCamara = await abrir(ANA, 'no-existe')
    expect(sinCamara.response.status).toBe(404)
    expect(sinCamara.error?.codigo).toBe('no_encontrado')
    // patio está desactivada: 422 validacion, aunque Laura tampoco tenga consentimiento.
    const desactivada = await abrir(LAURA, 'patio')
    expect(desactivada.response.status).toBe(422)
    expect(desactivada.error).toEqual({ codigo: 'validacion', detalle: 'La cámara está desactivada: actívala antes de inscribir.' })
    const sinConsentimiento = await abrir(LAURA)
    expect(sinConsentimiento.response.status).toBe(422)
    expect(sinConsentimiento.error?.codigo).toBe('sin_consentimiento')
    const malEscrita = await api.POST('/api/v1/inscripciones', { body: { persona_id: 'ana', dispositivo: 'entrada' } })
    expect(malEscrita.response.status).toBe(422)
    expect(malEscrita.error?.detalle).toBe('Los datos no son válidos: revisa «persona_id».')
  })
})

describe('RF-03 · C2, C3 y C6 · avance de la inscripción', () => {
  it('RF-03 · C6 · avanza cada 2 s con el guion: rechazos con su motivo y completada a los 14 s', async () => {
    const { id } = await abrirBien(ANA)
    pasar(3 * PASO_MS)
    expect(await ver(id)).toMatchObject({ estado: 'activa', muestras: 2, ultimo_motivo: 'cara_pequena' })
    pasar(2 * PASO_MS)
    // Una muestra aceptada después del rechazo no borra el motivo; el siguiente rechazo lo cambia.
    expect(await ver(id)).toMatchObject({ estado: 'activa', muestras: 3, ultimo_motivo: 'borrosa' })
    pasar(2 * PASO_MS)
    const completada = await ver(id)
    expect(completada).toMatchObject({ estado: 'completada', muestras: 5 })
    expect(Date.parse(completada.terminada ?? '')).toBe(INICIO.getTime() + 7 * PASO_MS)
    // RF-03 · C3: la cámara vuelve a reconocer, y las muestras quedan en la persona.
    const camara = await api.GET('/api/v1/dispositivos/{codigo}', { params: { path: { codigo: 'entrada' } } })
    expect(camara.data).toMatchObject({ modo: 'reconocer', inscripcion_activa: null })
    const persona = await api.GET('/api/v1/personas/{persona_id}', { params: { path: { persona_id: ANA } } })
    expect(persona.data?.muestras).toBe(10)
  })

  it('RF-03 · C4 · vence a los 120 s y una cámara sin conexión no recibe muestras', async () => {
    const { id } = await abrirBien(CARLOS, 'salida')
    pasar(VENCE_MS - 1000)
    expect(await ver(id)).toMatchObject({ estado: 'activa', muestras: 0 })
    pasar(1000)
    const vencida = await ver(id)
    expect(vencida).toMatchObject({ estado: 'vencida', muestras: 0 })
    expect(vencida.terminada).toBe(vencida.vence)
  })

  it('R9 · vencida sin revisar: al abrir otra en la misma cámara, la anterior queda vencida y la nueva se abre', async () => {
    const anterior = await abrirBien(CARLOS, 'salida')
    pasar(130_000)
    await abrirBien(ANA, 'salida')
    expect((await ver(anterior.id)).estado).toBe('vencida')
  })
})

describe('RF-03 · C5 · una sola activa por cámara, y cancelar', () => {
  it('RF-03 · C5 · otra en la misma cámara responde 409 inscripcion_activa; en otra cámara, no', async () => {
    await abrirBien(ANA)
    const segunda = await abrir(CARLOS)
    expect(segunda.response.status).toBe(409)
    expect(segunda.error).toEqual({ codigo: 'inscripcion_activa', detalle: 'Ya hay una inscripción activa en la cámara entrada.' })
    await abrirBien(CARLOS, 'salida')
  })

  it('RF-03 · C5 · cancela (204), conserva las muestras y no cancela dos veces (409 inscripcion_terminada)', async () => {
    const { id } = await abrirBien(ANA)
    pasar(2 * PASO_MS)
    const cancelada = await api.DELETE('/api/v1/inscripciones/{inscripcion_id}', rutaInscripcion(id))
    expect(cancelada.response.status).toBe(204)
    expect(await ver(id)).toMatchObject({ estado: 'cancelada', muestras: 2 })
    const otraVez = await api.DELETE('/api/v1/inscripciones/{inscripcion_id}', rutaInscripcion(id))
    expect(otraVez.response.status).toBe(409)
    // El mismo texto del servidor (tarea B2).
    expect(otraVez.error).toEqual({ codigo: 'inscripcion_terminada', detalle: 'La inscripción ya terminó: no se puede cancelar.' })
    const noExiste = await api.GET('/api/v1/inscripciones/{inscripcion_id}', rutaInscripcion('00000000-0000-4000-8000-999999999999'))
    expect(noExiste.response.status).toBe(404)
  })

  it('RF-02 · C5 · revocar el consentimiento cancela la inscripción activa de la persona', async () => {
    const { id } = await abrirBien(ANA)
    const revocar = await api.DELETE('/api/v1/personas/{persona_id}/consentimiento', { params: { path: { persona_id: ANA } } })
    expect(revocar.response.status).toBe(204)
    expect((await ver(id)).estado).toBe('cancelada')
  })
})
