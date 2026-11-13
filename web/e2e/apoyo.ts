/**
 * Nombre: apoyo.ts
 * Descripción: Pasos comunes de las pruebas de Playwright: entrar con las credenciales del simulacro, elegir una opción por su texto y abrir una inscripción.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import { expect, type Locator, type Page } from '@playwright/test'
import { CREDENCIALES_SIMULACRO } from '../src/simulacro/credenciales'

/** Elige la opción de un <select> que contiene el texto (las opciones llevan datos extra, como «· 5 muestras»). */
export async function elegir(lista: Locator, texto: string): Promise<void> {
  const opcion = lista.locator('option', { hasText: texto })
  await expect(opcion).toHaveCount(1)
  await lista.selectOption((await opcion.getAttribute('value')) ?? '')
}

/**
 * Desde la pantalla Inscripción, abre una para la persona en la cámara y espera su avance. Salida está sin
 * conexión en el simulacro: su inscripción no recibe muestras y sigue activa, sin carreras con el reloj.
 */
export async function abrirInscripcion(page: Page, persona: string, camara = 'Salida (salida)'): Promise<void> {
  await elegir(page.getByLabel('Persona'), persona)
  await elegir(page.getByLabel('Cámara'), camara)
  await page.getByRole('button', { name: 'Abrir inscripción' }).click()
  await expect(page).toHaveURL(/\/inscripcion\/[0-9a-f-]{36}$/)
  await expect(page.getByRole('heading', { level: 1, name: `Inscripción de ${persona}` })).toBeVisible()
}

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
