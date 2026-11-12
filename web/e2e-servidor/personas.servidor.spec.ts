/**
 * Nombre: personas.servidor.spec.ts
 * Descripción: Personas y consentimiento contra el servidor real (RF-02 · C1 a C5, RF-09 · C1): entrar, buscar con y sin tildes, paginar, crear, editar, activar y desactivar, y el consentimiento en web y en papel. Borra al final todo lo que crea.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { expect, request, test, type APIRequestContext, type Page } from '@playwright/test'

const API = 'http://localhost:8000'
// Una marca por corrida: va en el documento y en el nombre de cada persona de prueba, para encontrarlas y borrarlas.
const CORRIDA = Date.now().toString(36).slice(-6)
const DOCUMENTO = (numero: number) => `E2E-${CORRIDA}-${String(numero).padStart(2, '0')}`
const NOMBRE = (numero: number) => `Prueba Núñez ${CORRIDA} ${String(numero).padStart(2, '0')}`

function credenciales() {
  const correo = process.env.E2E_CORREO
  const clave = process.env.E2E_CLAVE
  if (!correo || !clave) throw new Error('Corre estas pruebas con «npm run e2e:servidor»: lee las credenciales de infra/.env')
  return { correo, clave }
}

/** Una sesión de la API, para preparar y borrar los datos de prueba sin pasar por la web. */
async function sesionApi(): Promise<APIRequestContext> {
  const contexto = await request.newContext({ baseURL: API })
  const respuesta = await contexto.post('/api/v1/sesion', { data: credenciales() })
  expect(respuesta.status(), 'el administrador de infra/.env no pudo entrar').toBe(200)
  return contexto
}

async function entrar(page: Page, destino = '/personas') {
  const { correo, clave } = credenciales()
  await page.goto(destino)
  await expect(page).toHaveURL(/\/entrar/)
  await page.getByLabel('Correo').fill(correo)
  await page.getByLabel('Clave').fill(clave)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).not.toHaveURL(/\/entrar/)
}

test.describe.configure({ mode: 'serial' })

let api: APIRequestContext

test.beforeAll(async () => {
  api = await sesionApi()
  // 11 personas: una página de 10 y otra de 1.
  for (let numero = 1; numero <= 11; numero += 1) {
    const respuesta = await api.post('/api/v1/personas', {
      data: { documento: DOCUMENTO(numero), nombre: NOMBRE(numero), rol: 'estudiante' },
    })
    expect(respuesta.status()).toBe(201)
  }
})

test.afterAll(async () => {
  // Borra todo lo de esta corrida, aunque alguna prueba haya fallado a mitad (RF-12 · C2).
  const respuesta = await api.get('/api/v1/personas', { params: { q: CORRIDA, por_pagina: 100 } })
  const { elementos } = (await respuesta.json()) as { elementos: Array<{ id: string; documento: string }> }
  for (const persona of elementos.filter((p) => p.documento.startsWith(`E2E-${CORRIDA}-`))) {
    expect((await api.delete(`/api/v1/personas/${persona.id}`)).status()).toBe(204)
  }
  const quedan = await api.get('/api/v1/personas', { params: { q: CORRIDA } })
  expect(((await quedan.json()) as { total: number }).total).toBe(0)
  await api.dispose()
})

test('RF-09 · C1 · entra con el administrador de infra/.env y rechaza una clave errada', async ({ page }) => {
  const { correo } = credenciales()
  await page.goto('/personas')
  await page.getByLabel('Correo').fill(correo)
  await page.getByLabel('Clave').fill('una-clave-que-no-es')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('alert')).toContainText('El correo o la clave no coinciden')
  await page.getByLabel('Clave').fill(credenciales().clave)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Personas' })).toBeVisible()
})

test('RF-02 · C1 · busca con y sin tildes y pagina', async ({ page }) => {
  await entrar(page)
  const filas = page.locator('tbody tr')

  await page.getByLabel('Buscar').fill(`nunez ${CORRIDA}`)
  await expect(page.getByText('11 resultados')).toBeVisible()
  await expect(filas).toHaveCount(10)
  await expect(page.getByText('1–10 de 11 · página 1 de 2')).toBeVisible()
  await page.getByRole('link', { name: 'Siguiente' }).click()
  await expect(page.getByText('11–11 de 11 · página 2 de 2')).toBeVisible()
  await expect(filas).toHaveCount(1)

  await page.getByLabel('Buscar').fill(`Núñez ${CORRIDA} 03`)
  await expect(filas).toHaveCount(1)
  await expect(filas.first()).toContainText(NOMBRE(3))
  await expect(filas.first()).toContainText(DOCUMENTO(3))
})

test('RF-02 · C1 · crea y edita una persona, sin repetir documentos', async ({ page }) => {
  await entrar(page, '/personas/nueva')
  await page.getByLabel('Nombre completo').fill(`Prueba Ávila ${CORRIDA}`)
  await page.getByLabel('Documento').fill(DOCUMENTO(1))
  await page.getByRole('button', { name: 'Crear persona' }).click()
  // 409 documento_duplicado del servidor, junto al campo.
  await expect(page.getByLabel('Documento')).toBeFocused()
  await expect(page.getByLabel('Documento')).toHaveAttribute('aria-invalid', 'true')

  await page.getByLabel('Documento').fill(DOCUMENTO(50))
  await page.getByLabel('Rol').selectOption({ label: 'Docente' })
  await page.getByRole('button', { name: 'Crear persona' }).click()
  await expect(page.getByRole('heading', { level: 1, name: `Prueba Ávila ${CORRIDA}` })).toBeVisible()
  await expect(page.getByText('Persona creada.')).toBeVisible()

  await page.getByRole('link', { name: 'Editar' }).click()
  await page.getByLabel('Nombre completo').fill(`Prueba Ávila Editada ${CORRIDA}`)
  await page.getByRole('button', { name: 'Guardar cambios' }).click()
  await expect(page.getByRole('heading', { level: 1, name: `Prueba Ávila Editada ${CORRIDA}` })).toBeVisible()
  await expect(page.getByText('Cambios guardados.')).toBeVisible()
})

test('RF-02 · C1 · desactiva y vuelve a activar a una persona', async ({ page }) => {
  await entrar(page)
  await page.getByLabel('Buscar').fill(DOCUMENTO(2))
  await page.getByRole('link', { name: NOMBRE(2) }).click()
  const datos = page.getByRole('region', { name: 'Datos' })
  await datos.getByRole('button', { name: 'Desactivar' }).click()
  await expect(datos.getByText('Inactiva')).toBeVisible()
  await datos.getByRole('button', { name: 'Activar' }).click()
  await expect(datos.getByText('Activa', { exact: true })).toBeVisible()
})

test('RF-02 · C2, C3 y C5 · registra el consentimiento en la web y lo revoca', async ({ page }) => {
  await entrar(page)
  await page.getByLabel('Buscar').fill(DOCUMENTO(4))
  await page.getByRole('link', { name: NOMBRE(4) }).click()
  const inscribir = page.getByRole('button', { name: 'Inscribir' })
  await expect(inscribir).toBeDisabled()
  await expect(page.getByText('El consentimiento es opcional')).toBeVisible()

  await page.getByRole('checkbox', { name: /acepta el tratamiento de sus datos biométricos/ }).check()
  await page.getByRole('button', { name: 'Registrar consentimiento' }).click()
  await expect(page.getByText('Consentimiento registrado. Ya puedes inscribir a esta persona.')).toBeVisible()
  await expect(inscribir).toBeEnabled()

  await page.getByRole('button', { name: 'Revocar consentimiento' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Revocar y borrar huellas' }).click()
  await expect(inscribir).toBeDisabled()
  await expect(page.locator('.historial__item')).toHaveCount(1)
})

test('RF-02 · C2 · registra el consentimiento en papel con la fecha de la firma', async ({ page }) => {
  await entrar(page)
  await page.getByLabel('Buscar').fill(DOCUMENTO(5))
  await page.getByRole('link', { name: NOMBRE(5) }).click()
  await page.getByRole('radio', { name: /En papel/ }).check()
  // Ayer a esta hora, en hora de Colombia, con el formato de datetime-local.
  const ayer = new Date(Date.now() - 24 * 60 * 60 * 1000 - 5 * 60 * 60 * 1000).toISOString().slice(0, 16)
  await page.getByLabel('Fecha y hora de la firma').fill(ayer)
  await page.getByRole('checkbox', { name: /acepta el tratamiento de sus datos biométricos/ }).check()
  await page.getByRole('button', { name: 'Registrar consentimiento' }).click()
  await expect(page.getByText('Consentimiento registrado. Ya puedes inscribir a esta persona.')).toBeVisible()
  await expect(page.locator('.historial__item').first()).toContainText('Versión 1.0 · En papel')
})

test('RF-10 · C3 · la lista de cámaras del servidor se ve en Cámaras, sin cambiar nada', async ({ page }) => {
  const respuesta = await api.get('/api/v1/dispositivos')
  const camaras = (await respuesta.json()) as Array<{ codigo: string; nombre: string }>
  await entrar(page, '/camaras')
  await expect(page.getByRole('heading', { level: 1, name: 'Cámaras' })).toBeVisible()
  if (camaras.length === 0) {
    await expect(page.getByText('Todavía no hay cámaras')).toBeVisible()
    return
  }
  await expect(page.locator('tbody tr')).toHaveCount(camaras.length)
  for (const camara of camaras) await expect(page.getByRole('link', { name: camara.nombre })).toBeVisible()
})
