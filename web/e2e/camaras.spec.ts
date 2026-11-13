/**
 * Nombre: camaras.spec.ts
 * Descripción: Pruebas de punta a punta de la pantalla Cámaras con el simulacro: crear y ver el token una sola vez, cambiarlo, editar, el código servidor y la inscripción activa (RF-10 · C1 a C3).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { expect, test } from '@playwright/test'
import { abrirInscripcion, entrar } from './apoyo'

const PATRON_TOKEN = /^[A-Za-z0-9_-]{43}$/

test('RF-10 · C1 · crea una cámara y muestra su token una sola vez', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await entrar(page, '/camaras')
  await expect(page.locator('tbody tr')).toHaveCount(3)

  await page.getByRole('link', { name: 'Nueva cámara' }).click()
  await page.getByLabel('Código').fill('porteria')
  await page.getByLabel('Nombre').fill('Portería')
  await page.getByLabel('Tipo').selectOption({ label: 'TinyML' })
  await page.getByRole('button', { name: 'Crear cámara' }).click()

  const dialogo = page.getByRole('dialog', { name: 'Token de la cámara Portería' })
  await expect(dialogo).toBeVisible()
  await expect(dialogo).toContainText('Cópialo ahora: no se vuelve a mostrar.')
  await expect(dialogo).toContainText('$env:TOKEN_CAMARA')
  const campo = dialogo.getByLabel('Token')
  await expect(campo).toBeFocused()
  const token = await campo.inputValue()
  expect(token).toMatch(PATRON_TOKEN)

  await dialogo.getByRole('button', { name: 'Copiar' }).click()
  await expect(dialogo.getByRole('button', { name: 'Copiado' })).toBeVisible()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(token)

  await dialogo.getByRole('button', { name: 'Ya lo copié' }).click()
  await expect(page).toHaveURL(/\/camaras$/)
  await expect(page.getByRole('status').filter({ hasText: 'Cámara Portería creada.' })).toBeVisible()
  await expect(page.locator('tbody tr')).toHaveCount(4)
  // El token no vuelve a aparecer: ni en la lista, ni en la ficha, ni en el almacenamiento del navegador.
  await expect(page.locator('body')).not.toContainText(token)
  await page.getByRole('link', { name: 'Portería' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Portería' })).toBeVisible()
  await expect(page.locator('body')).not.toContainText(token)
  const guardado = await page.evaluate(() => JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage }))
  expect(guardado).not.toContain(token)
  expect(page.url()).not.toContain(token)
})

test('RF-10 · C2 · cambia el token con confirmación y lo muestra una sola vez', async ({ page }) => {
  await entrar(page, '/camaras')
  await page.getByRole('link', { name: 'Entrada' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Entrada' })).toBeVisible()

  const cambiar = page.getByRole('button', { name: 'Cambiar token' })
  await cambiar.click()
  const confirmacion = page.getByRole('dialog', { name: '¿Cambiar el token de Entrada?' })
  await expect(confirmacion).toContainText('El token actual deja de servir de inmediato')
  await confirmacion.getByRole('button', { name: 'Cambiar token' }).click()

  const dialogo = page.getByRole('dialog', { name: 'Token de la cámara Entrada' })
  await expect(dialogo).toContainText('El token anterior ya no sirve.')
  const token = await dialogo.getByLabel('Token').inputValue()
  expect(token).toMatch(PATRON_TOKEN)
  await dialogo.getByRole('button', { name: 'Ya lo copié' }).click()

  await expect(page.getByText('Token cambiado. El anterior ya no sirve.')).toBeVisible()
  await expect(page.locator('body')).not.toContainText(token)
  await expect(cambiar).toBeFocused()
})

test('RF-10 · C1 · el código servidor se rechaza junto a su campo, y también un código repetido', async ({ page }) => {
  await entrar(page, '/camaras/nueva')
  await page.getByLabel('Código').fill('servidor')
  await page.getByLabel('Nombre').fill('Servidor')
  await page.getByRole('button', { name: 'Crear cámara' }).click()
  await expect(page.getByText('«servidor» está reservado para el servidor. Elige otro código.')).toBeVisible()
  await expect(page.getByLabel('Código')).toBeFocused()
  await expect(page.getByLabel('Código')).toHaveAttribute('aria-invalid', 'true')
  await expect(page.getByRole('dialog')).toHaveCount(0)

  // 409 codigo_duplicado: lo responde el simulacro y va junto al código.
  await page.getByLabel('Código').fill('entrada')
  await page.getByRole('button', { name: 'Crear cámara' }).click()
  await expect(page.getByText('Ya hay una cámara con el código entrada.')).toBeVisible()
  await expect(page.getByLabel('Código')).toBeFocused()

  // Una de respaldo necesita su URL de captura.
  await page.getByLabel('Código').fill('patio-2')
  await page.getByLabel('Tipo').selectOption({ label: 'Respaldo' })
  await page.getByRole('button', { name: 'Crear cámara' }).click()
  await expect(page.getByText('Una cámara de respaldo necesita su URL de captura.')).toBeVisible()
  await expect(page.getByLabel(/URL de captura/)).toBeFocused()
})

test('RF-10 · C1 · edita la cámara y la desactiva: deja de ofrecerse para inscribir', async ({ page }) => {
  await entrar(page, '/camaras')
  await page.getByRole('link', { name: 'Salida' }).click()
  await page.getByLabel('Nombre').fill('Salida norte')
  await page.getByRole('checkbox', { name: /Cámara activa/ }).uncheck()
  await page.getByRole('button', { name: 'Guardar cambios' }).click()
  await expect(page.getByText('Cambios guardados.')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1, name: 'Salida norte' })).toBeVisible()

  await page.getByRole('link', { name: 'Cámaras', exact: true }).first().click()
  const fila = page.locator('tbody tr').filter({ hasText: 'Salida norte' })
  await expect(fila).toContainText('Inactiva')

  await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: /Inscripción/ }).click()
  await expect(page.getByLabel('Cámara')).not.toContainText('Salida')
})

test('RF-10 · C3 · una cámara con inscripción activa la muestra en Cámaras', async ({ page }) => {
  await entrar(page, '/inscripcion')
  await abrirInscripcion(page, 'Diana Marcela Ortiz Charry')
  const inscripcion = page.url()

  await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: /Cámaras/ }).click()
  const fila = page.locator('tbody tr').filter({ hasText: 'Salida' })
  await expect(fila).toContainText('Inscribiendo')
  await expect(fila).toContainText(/0 de 5 · vence en [12]:\d\d/)
  await expect(page.locator('tbody tr').filter({ hasText: 'Entrada' })).toContainText('Reconoce')

  await fila.getByRole('link', { name: 'Ver la inscripción' }).click()
  await expect(page).toHaveURL(inscripcion)
  await expect(page.getByRole('heading', { level: 1, name: 'Inscripción de Diana Marcela Ortiz Charry' })).toBeVisible()
  // La cámara, en su ficha, también la muestra.
  await page.goBack()
  await page.getByRole('link', { name: 'Salida' }).click()
  await expect(page.getByRole('region', { name: 'Estado' })).toContainText('Inscribiendo')
})
