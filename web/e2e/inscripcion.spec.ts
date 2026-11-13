/**
 * Nombre: inscripcion.spec.ts
 * Descripción: Pruebas de punta a punta de la pantalla Inscripción con el simulacro: avance hasta completada, motivo de rechazo, cancelar y el 409 inscripcion_activa (RF-03 · C1, C5 y C6).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { expect, test } from '@playwright/test'
import { abrirInscripcion, elegir, entrar } from './apoyo'

// El simulacro recibe una cara cada 2 s en la cámara Entrada y completa la inscripción a los 14 s.
const GUION = { timeout: 25_000 }

test('RF-03 · C1 y C6 · abre una inscripción y muestra «Muestra n de 5» hasta completada', async ({ page }) => {
  await entrar(page, '/inscripcion')
  await expect(page.getByRole('heading', { level: 1, name: 'Inscripción' })).toBeVisible()
  await abrirInscripcion(page, 'Ana María Gómez Rojas', 'Entrada (entrada)')

  const avance = page.getByRole('progressbar', { name: 'Avance de la inscripción' })
  await expect(page.getByText('Muestra 0 de 5')).toBeVisible()
  await expect(page.getByText(/^Vence en [12]:\d\d$/)).toBeVisible()
  await expect(page.getByText('Muestra 2 de 5')).toBeVisible(GUION)
  await expect(avance).toHaveAttribute('aria-valuenow', '2')

  await expect(page.getByText('Inscripción completada')).toBeVisible(GUION)
  await expect(page.getByText('Muestra 5 de 5')).toBeVisible()
  await expect(avance).toHaveAttribute('aria-valuenow', '5')
  await expect(page.getByRole('button', { name: 'Cancelar inscripción' })).toHaveCount(0)

  // Ana tenía 5 muestras: la ficha ahora dice 10.
  await page.getByRole('link', { name: 'Ver la ficha' }).click()
  await expect(page.getByText('10 muestras guardadas')).toBeVisible()
})

test('RF-03 · C6 · un rechazo muestra su motivo en español y qué hacer', async ({ page }) => {
  await entrar(page, '/inscripcion')
  await abrirInscripcion(page, 'Natalia Hernández Polo', 'Entrada (entrada)')

  // El guion rechaza la tercera cara por cara_pequena y la quinta por borrosa.
  await expect(page.getByText('Último rechazo: La cara se ve muy pequeña.', { exact: true })).toBeVisible(GUION)
  await expect(page.getByText('Acércate a la cámara.', { exact: true })).toBeVisible()
  // Y se anuncia una sola vez, en la región que vigilan los lectores de pantalla.
  const anuncio = page.locator('p[aria-live="polite"]').filter({ hasText: 'Último rechazo' })
  await expect(anuncio).toHaveText('Último rechazo: La cara se ve muy pequeña. Acércate a la cámara.')

  await expect(page.getByText('Después se aceptó otra muestra.')).toBeVisible(GUION)
  await expect(page.getByText('Último rechazo: La imagen salió borrosa.', { exact: true })).toBeVisible(GUION)
  await expect(page.getByText('Quédate quieto un momento frente a la cámara.', { exact: true })).toBeVisible()
  await expect(anuncio).toHaveText('Último rechazo: La imagen salió borrosa. Quédate quieto un momento frente a la cámara.')
})

test('RF-03 · C5 · cancela con confirmación y conserva las muestras', async ({ page }) => {
  await entrar(page, '/inscripcion')
  await abrirInscripcion(page, 'Andrés Felipe Trujillo Vargas')
  await expect(page.getByText('La cámara Salida está sin conexión: no llegarán muestras hasta que se conecte.')).toBeVisible()

  await page.getByRole('button', { name: 'Cancelar inscripción' }).click()
  const dialogo = page.getByRole('dialog', { name: '¿Cancelar la inscripción de Andrés Felipe Trujillo Vargas?' })
  await expect(dialogo).toBeVisible()
  await expect(dialogo.getByRole('button', { name: 'Seguir inscribiendo' })).toBeFocused()
  await dialogo.getByRole('button', { name: 'Cancelar inscripción' }).click()

  const estado = page.getByRole('status').filter({ hasText: 'Inscripción cancelada' })
  await expect(estado).toBeVisible()
  await expect(estado).toContainText('No hay muestras aceptadas. La cámara Salida vuelve a reconocer.')
  await expect(page.getByRole('button', { name: 'Cancelar inscripción' })).toHaveCount(0)
  await page.getByRole('link', { name: 'Abrir otra inscripción' }).click()
  await expect(page.getByLabel('Persona').locator('option:checked')).toContainText('Andrés Felipe Trujillo Vargas')
})

test('RF-03 · C5 · con la cámara ocupada (409 inscripcion_activa), ver la que ya estaba y cancelarla para abrir la nueva', async ({
  page,
}) => {
  await entrar(page, '/inscripcion')
  await abrirInscripcion(page, 'Ana María Gómez Rojas')
  const deAna = page.url()

  // La que ya estaba se ve en «En curso».
  await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: /Inscripción/ }).click()
  await expect(page.getByRole('region', { name: 'En curso' })).toContainText('Salida · Ana María Gómez Rojas')

  await elegir(page.getByLabel('Persona'), 'Carlos Andrés Ramírez Polanía')
  await elegir(page.getByLabel('Cámara'), 'Salida (salida) · inscribiendo')
  await page.getByRole('button', { name: 'Abrir inscripción' }).click()
  const ocupada = page.getByRole('alert').filter({ hasText: 'La cámara Salida ya está inscribiendo a Ana María Gómez Rojas' })
  await expect(ocupada).toBeVisible()
  await expect(ocupada).toContainText(/Muestra 0 de 5 · vence en [12]:\d\d/)

  // Ver: sigue el avance de la de Ana, como si se hubiera abierto aquí.
  await ocupada.getByRole('link', { name: 'Ver su avance' }).click()
  await expect(page).toHaveURL(deAna)
  await expect(page.getByRole('heading', { level: 1, name: 'Inscripción de Ana María Gómez Rojas' })).toBeVisible()

  // Cancelarla y abrir la nueva.
  await page.goBack()
  await elegir(page.getByLabel('Persona'), 'Carlos Andrés Ramírez Polanía')
  await elegir(page.getByLabel('Cámara'), 'Salida (salida)')
  await page.getByRole('button', { name: 'Abrir inscripción' }).click()
  await page.getByRole('button', { name: 'Cancelarla y abrir la nueva' }).click()
  const dialogo = page.getByRole('dialog', { name: '¿Cancelar la inscripción de Ana María Gómez Rojas?' })
  await dialogo.getByRole('button', { name: 'Cancelar y abrir la nueva' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Inscripción de Carlos Andrés Ramírez Polanía' })).toBeVisible()
  expect(page.url()).not.toBe(deAna)
})

test('RF-02 · C4 · solo se elige a quien tiene consentimiento vigente, y solo cámaras activas', async ({ page }) => {
  await entrar(page, '/inscripcion')
  const personas = page.getByLabel('Persona').locator('option')
  // Seis personas de ejemplo tienen consentimiento vigente, más la opción vacía.
  await expect(personas).toHaveCount(7)
  await expect(page.getByLabel('Persona')).not.toContainText('Laura Valentina Cuéllar Díaz')
  await expect(page.getByLabel('Persona')).toContainText('Juan Sebastián Rojas Quintero · inactiva · 5 muestras')
  // Patio está desactivada: no aparece.
  await expect(page.getByLabel('Cámara').locator('option')).toHaveCount(3)
  await expect(page.getByLabel('Cámara')).not.toContainText('Patio')

  await page.getByRole('button', { name: 'Abrir inscripción' }).click()
  await expect(page.getByText('Elige a la persona que se inscribe.')).toBeVisible()
  await expect(page.getByText('Elige la cámara.')).toBeVisible()
  await expect(page.getByLabel('Persona')).toBeFocused()
})
