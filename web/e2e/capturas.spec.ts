/**
 * Nombre: capturas.spec.ts
 * Descripción: Capturas de cada pantalla a 1280×720 y 1440×900 en web/capturas/ (ignorada por Git) para revisarlas (RF-09 · C3).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import { fileURLToPath } from 'node:url'
import { expect, test, type Page } from '@playwright/test'
import { abrirInscripcion, elegir, entrar } from './apoyo'

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

    // Inscripción (RF-03): desde la ficha, con Ana ya elegida.
    await page.getByRole('button', { name: 'Inscribir' }).click()
    await expect(page.getByLabel('Persona').locator('option:checked')).toContainText('Ana María Gómez Rojas')
    await elegir(page.getByLabel('Cámara'), 'Entrada (entrada)')
    await capturar('09-inscripcion-abrir')

    await page.getByRole('button', { name: 'Abrir inscripción' }).click()
    await expect(page.getByText('Último rechazo: La cara se ve muy pequeña.', { exact: true })).toBeVisible({
      timeout: 25_000,
    })
    await capturar('10-inscripcion-avance-con-rechazo')
    await expect(page.getByText('Inscripción completada')).toBeVisible({ timeout: 25_000 })
    await capturar('11-inscripcion-completada')

    // Una inscripción en Salida (sin conexión: sigue activa) y otra pedida en la misma cámara: 409.
    await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: /Inscripción/ }).click()
    await abrirInscripcion(page, 'Carlos Andrés Ramírez Polanía')
    await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: /Inscripción/ }).click()
    await elegir(page.getByLabel('Persona'), 'Natalia Hernández Polo')
    await elegir(page.getByLabel('Cámara'), 'Salida (salida)')
    await page.getByRole('button', { name: 'Abrir inscripción' }).click()
    await expect(page.getByText('La cámara Salida ya está inscribiendo a Carlos Andrés Ramírez Polanía')).toBeVisible()
    await capturar('12-inscripcion-camara-ocupada')

    // Cámaras (RF-10)
    await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: /Cámaras/ }).click()
    await expect(page.locator('tbody tr').filter({ hasText: 'Salida' })).toContainText('Inscribiendo')
    await capturar('13-camaras')

    await page.getByRole('link', { name: 'Nueva cámara' }).click()
    await page.getByLabel('Código').fill('servidor')
    await page.getByLabel('Tipo').selectOption({ label: 'Respaldo' })
    await page.getByRole('button', { name: 'Crear cámara' }).click()
    await expect(page.getByText('«servidor» está reservado para el servidor. Elige otro código.')).toBeVisible()
    await capturar('14-nueva-camara-con-errores')

    await page.getByLabel('Código').fill('porteria')
    await page.getByLabel('Nombre').fill('Portería')
    await page.getByLabel('Tipo').selectOption({ label: 'TinyML' })
    await page.getByRole('button', { name: 'Crear cámara' }).click()
    await expect(page.getByRole('dialog', { name: 'Token de la cámara Portería' })).toBeVisible()
    await capturar('15-token-de-la-camara')
    await page.getByRole('button', { name: 'Ya lo copié' }).click()

    await page.getByRole('link', { name: 'Salida' }).click()
    await expect(page.getByRole('region', { name: 'Estado' })).toContainText('Inscribiendo')
    await capturar('16-ficha-de-la-camara')
  })
}
