/**
 * Nombre: apoyo.ts
 * Descripción: Pasos comunes de las pruebas de Playwright: entrar con las credenciales del simulacro.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { expect, type Page } from '@playwright/test'
import { CREDENCIALES_SIMULACRO } from '../src/simulacro/credenciales'

/**
 * Abre una pantalla sin sesión, entra y espera volver a ella. El simulacro vive en la pestaña:
 * después de entrar, las pruebas navegan con clics, porque recargar vuelve a los datos de ejemplo.
 */
export async function entrar(page: Page, destino = '/personas'): Promise<void> {
  await page.goto(destino)
  await expect(page).toHaveURL(/\/entrar/)
  await page.getByLabel('Correo').fill(CREDENCIALES_SIMULACRO.correo)
  await page.getByLabel('Clave').fill(CREDENCIALES_SIMULACRO.clave)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).toHaveURL(new RegExp(`${destino.replace(/[?]/g, '\\?')}$`))
}

/** Ayer a esta hora, en hora de Colombia, con el formato de un campo datetime-local. */
export function ayerEnColombia(): string {
  const ayer = Date.now() - 24 * 60 * 60 * 1000 - 5 * 60 * 60 * 1000
  return new Date(ayer).toISOString().slice(0, 16)
}
