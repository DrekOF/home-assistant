/**
 * Nombre: capturas.spec.ts
 * Descripción: Capturas de cada pantalla a 1280×720 y 1440×900 en web/capturas/ (ignorada por Git) para revisarlas (RF-09 · C3).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { fileURLToPath } from 'node:url'
import { expect, test, type Page } from '@playwright/test'
import { entrar } from './apoyo'

const CAPTURAS = fileURLToPath(new URL('../capturas/', import.meta.url))
const TAMANOS = [
  { width: 1280, height: 720 },
  { width: 1440, height: 900 },
]

for (const tamano of TAMANOS) {
  test(`RF-09 · C3 · capturas de las pantallas a ${tamano.width}×${tamano.height}`, async ({ page }) => {
    await page.setViewportSize(tamano)
    const capturar = async (nombre: string, pantalla: Page = page) => {
      await pantalla.evaluate(() => document.fonts.ready)
      await pantalla.screenshot({
        path: `${CAPTURAS}${tamano.width}x${tamano.height}/${nombre}.png`,
        fullPage: true,
        animations: 'disabled',
      })
    }

    await page.goto('/entrar')
    await expect(page.getByRole('heading', { level: 1, name: 'Entrar' })).toBeVisible()
    await capturar('01-entrar')

    await entrar(page)
    await expect(page.locator('tbody tr')).toHaveCount(10)
    await capturar('02-personas')

    await page.getByLabel('Buscar').fill('zzz')
    await expect(page.getByText('Nadie coincide con «zzz»')).toBeVisible()
    await capturar('03-personas-sin-resultados')
    await page.getByRole('button', { name: 'Quitar los filtros' }).click()

    await page.getByRole('link', { name: 'Nueva persona' }).click()
    await page.getByLabel('Horario').selectOption({ label: 'Clase de IA' })
    await page.getByRole('button', { name: 'Crear persona' }).click()
    await expect(page.getByText('Escribe el nombre completo.')).toBeVisible()
    await capturar('04-nueva-persona-con-errores')
    await page.getByRole('link', { name: 'Cancelar' }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Salir sin guardar' }).click()

    await page.getByRole('link', { name: 'Laura Valentina Cuéllar Díaz' }).click()
    await expect(page.getByRole('region', { name: /Texto de la autorización/ })).toBeVisible()
    await capturar('05-ficha-sin-consentimiento')

    // Valentina está en la página 2 (orden alfabético): se busca.
    await page.getByRole('link', { name: 'Personas', exact: true }).first().click()
    await page.getByLabel('Buscar').fill('ospina')
    await page.getByRole('link', { name: 'Valentina Ospina Cerquera' }).click()
    await expect(page.locator('.historial__item')).toHaveCount(1)
    await capturar('06-ficha-con-consentimiento-revocado')

    await page.getByRole('link', { name: 'Personas', exact: true }).first().click()
    await page.getByLabel('Buscar').fill('')
    await page.getByRole('link', { name: 'Ana María Gómez Rojas' }).click()
    await expect(page.getByRole('button', { name: 'Inscribir' })).toBeEnabled()
    await capturar('07-ficha-con-consentimiento')

    await page.getByRole('button', { name: 'Revocar consentimiento' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await capturar('08-revocar-consentimiento')
    await page.getByRole('dialog').getByRole('button', { name: 'Cancelar' }).click()

    await page.getByRole('button', { name: 'Inscribir' }).click()
    await expect(page.getByText('Vista previa del avance')).toBeVisible()
    await capturar('09-inscripcion-proximamente')
  })
}
