/**
 * Nombre: personas.spec.ts
 * Descripción: Pruebas de punta a punta con el simulacro: inicio de sesión, Personas y consentimiento (RF-09 · C1, RF-02 · C1 a C5).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import { expect, test } from '@playwright/test'
import { ayerEnColombia, entrar } from './apoyo'

test('RF-09 · C1 · sin sesión pide entrar, rechaza una clave errada y vuelve a la pantalla pedida', async ({ page }) => {
  await page.goto('/personas')
  await expect(page).toHaveURL(/\/entrar\?siguiente=%2Fpersonas$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Entrar' })).toBeVisible()

  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByText('Escribe tu correo.')).toBeVisible()
  await expect(page.getByLabel('Correo')).toBeFocused()

  await page.getByLabel('Correo').fill('admin@example.com')
  await page.getByLabel('Clave').fill('otra-clave')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('alert')).toContainText('El correo o la clave no coinciden')

  await page.getByLabel('Clave').fill('simulacro')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).toHaveURL(/\/personas$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Personas' })).toBeVisible()
  await expect(page).toHaveTitle('Personas · AccesIA')

  await page.getByRole('button', { name: 'Cerrar sesión' }).click()
  await expect(page).toHaveURL(/\/entrar$/)
})

test('RF-02 · C1 · busca sin tildes, filtra por estado, pagina y desactiva con deshacer', async ({ page }) => {
  await entrar(page)
  const filas = page.locator('tbody tr')
  await expect(filas).toHaveCount(10)
  await expect(page.getByText('1–10 de 12 · página 1 de 2')).toBeVisible()

  await page.getByLabel('Buscar').fill('nunez')
  await expect(page).toHaveURL(/q=nunez/)
  await expect(filas).toHaveCount(1)
  await expect(filas.first()).toContainText('Esteban Calderón Núñez')

  await page.getByLabel('Buscar').fill('')
  await page.getByLabel('Estado').selectOption('inactivas')
  await expect(page).toHaveURL(/estado=inactivas/)
  await expect(filas).toHaveCount(2)
  await expect(page.locator('tbody')).toContainText('Óscar Iván Cabrera Silva')

  // Cambiar de página es navegar: en los extremos el botón queda deshabilitado.
  await page.getByLabel('Estado').selectOption('todas')
  await expect(page.getByRole('button', { name: 'Anterior' })).toBeDisabled()
  await page.getByRole('link', { name: 'Siguiente' }).click()
  await expect(page).toHaveURL(/pagina=2/)
  await expect(page.getByText('11–12 de 12 · página 2 de 2')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  await page.getByRole('link', { name: 'Anterior' }).click()

  await page.getByRole('button', { name: 'Desactivar a Ana María Gómez Rojas' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'quedó inactiva' })).toContainText(
    'Ana María Gómez Rojas quedó inactiva.',
  )
  await expect(page.getByRole('button', { name: 'Activar a Ana María Gómez Rojas' })).toBeVisible()
  await page.getByRole('button', { name: 'Deshacer' }).click()
  await expect(page.getByRole('button', { name: 'Desactivar a Ana María Gómez Rojas' })).toBeVisible()
})

test('RF-02 · C1, C2, C3 y C4 · crea una persona, registra su consentimiento y solo entonces habilita «Inscribir»', async ({
  page,
}) => {
  await entrar(page)
  await page.getByRole('link', { name: 'Nueva persona' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Nueva persona' })).toBeVisible()

  // Las validaciones salen junto a cada campo y el foco va al primero con error.
  await page.getByRole('button', { name: 'Crear persona' }).click()
  await expect(page.getByText('Escribe el nombre completo.')).toBeVisible()
  await expect(page.getByLabel('Nombre completo')).toBeFocused()

  await page.getByLabel('Nombre completo').fill('Camila Andrea Torres Quintero')
  await page.getByLabel('Documento').fill('1075234567')
  await page.getByLabel('Rol').selectOption('docente')
  await page.getByLabel('Horario').selectOption({ label: 'Clase de IA' })
  await expect(page.getByText('Lun, 07:00, tolerancia de 10 min; mié, 18:00, tolerancia de 15 min')).toBeVisible()

  // El documento ya es de Ana: el servidor responde 409 documento_duplicado y el error sale en su campo.
  await page.getByRole('button', { name: 'Crear persona' }).click()
  await expect(page.getByText('Ya hay una persona con el documento 1075234567.')).toBeVisible()
  await page.getByLabel('Documento').fill('1075999888')
  await page.getByRole('button', { name: 'Crear persona' }).click()

  await expect(page.getByRole('heading', { level: 1, name: 'Camila Andrea Torres Quintero' })).toBeVisible()
  await expect(page.getByText('Persona creada.')).toBeVisible()
  const inscribir = page.getByRole('button', { name: 'Inscribir' })
  await expect(inscribir).toBeDisabled()
  await expect(page.getByText('Para inscribir a esta persona, primero registra su consentimiento.')).toBeVisible()

  // RF-02 · C3: el texto viene de la API, dice que es opcional y ofrece el registro manual.
  await expect(page.getByText('El consentimiento es opcional')).toBeVisible()
  await expect(page.getByText('Su asistencia se registra a mano en')).toBeVisible()
  const texto = page.getByRole('region', { name: 'Texto de la autorización, versión 1.0' })
  await expect(texto).toContainText('No es obligatorio.')
  await expect(texto).toContainText('No se guardan fotos de mi cara.')

  // Sin marcar la casilla no se registra.
  await page.getByRole('button', { name: 'Registrar consentimiento' }).click()
  await expect(page.getByText('Marca la casilla solo cuando la persona haya aceptado.')).toBeVisible()
  await expect(inscribir).toBeDisabled()

  // RF-02 · C2: en papel, con la fecha de la firma.
  await page.getByRole('radio', { name: /En papel/ }).check()
  await page.getByLabel('Fecha y hora de la firma').fill(ayerEnColombia())
  await page.getByRole('checkbox', { name: /acepta el tratamiento de sus datos biométricos/ }).check()
  await page.getByRole('button', { name: 'Registrar consentimiento' }).click()

  await expect(page.getByText('Consentimiento registrado. Ya puedes inscribir a esta persona.')).toBeVisible()
  await expect(inscribir).toBeEnabled()
  await expect(page.getByRole('definition').filter({ hasText: 'En papel' })).toBeVisible()
  await expect(page.locator('.historial__item')).toHaveCount(1)
  await expect(page.locator('.historial__item').first()).toContainText('Versión 1.0 · En papel')

  await inscribir.click()
  await expect(page).toHaveURL(/\/inscripcion\?persona=/)
  // Inscripción ya la tiene elegida: tiene consentimiento vigente.
  await expect(page.getByLabel('Persona').locator('option:checked')).toContainText('Camila Andrea Torres Quintero')
})

test('RF-02 · C5 · revocar pide confirmación, borra las huellas y vuelve a deshabilitar «Inscribir»', async ({ page }) => {
  await entrar(page)
  await page.getByRole('link', { name: 'Ana María Gómez Rojas' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Ana María Gómez Rojas' })).toBeVisible()
  const inscribir = page.getByRole('button', { name: 'Inscribir' })
  await expect(inscribir).toBeEnabled()
  await expect(page.getByText('5 muestras guardadas')).toBeVisible()

  // Cancelar no cambia nada.
  await page.getByRole('button', { name: 'Revocar consentimiento' }).click()
  const dialogo = page.getByRole('dialog', { name: '¿Revocar el consentimiento de Ana María Gómez Rojas?' })
  await expect(dialogo).toBeVisible()
  await expect(dialogo).toContainText('Se borran sus huellas (5 muestras)')
  await expect(dialogo.getByRole('button', { name: 'Cancelar' })).toBeFocused()
  await dialogo.getByRole('button', { name: 'Cancelar' }).click()
  await expect(dialogo).toBeHidden()
  await expect(inscribir).toBeEnabled()

  await page.getByRole('button', { name: 'Revocar consentimiento' }).click()
  await dialogo.getByRole('button', { name: 'Revocar y borrar huellas' }).click()
  await expect(dialogo).toBeHidden()
  await expect(page.getByText(/Consentimiento revocado: se borraron sus huellas/)).toBeVisible()
  await expect(inscribir).toBeDisabled()
  await expect(page.getByText('Ninguna guardada')).toBeVisible()
  await expect(page.locator('.historial__item').first()).toContainText('Revocado el ')
})

test('RF-02 · C1 · avisa antes de salir del formulario con cambios sin guardar', async ({ page }) => {
  await entrar(page)
  await page.getByRole('link', { name: 'Nueva persona' }).click()
  await page.getByLabel('Nombre completo').fill('Persona a medias')
  await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: 'Personas' }).click()
  const dialogo = page.getByRole('dialog', { name: '¿Salir sin guardar?' })
  await expect(dialogo).toBeVisible()
  await dialogo.getByRole('button', { name: 'Seguir editando' }).click()
  await expect(page.getByLabel('Nombre completo')).toHaveValue('Persona a medias')

  await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: 'Personas' }).click()
  await dialogo.getByRole('button', { name: 'Salir sin guardar' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Personas' })).toBeVisible()
})

test('Accesibilidad · teclado · salto al contenido, navegación y diálogo sin mouse', async ({ page }) => {
  await entrar(page)
  // Recién entrado, el foco está en el contenido y el siguiente Tab llega a su primera acción.
  await expect(page.locator('#contenido')).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Nueva persona' })).toBeFocused()

  // El salto al contenido es lo primero que se alcanza con Tab, aparece con el foco y lleva al contenido.
  const enfocables = page.locator('a[href], button:not([disabled]), input, select, [tabindex="0"]')
  await expect(enfocables.first()).toHaveText('Saltar al contenido')
  const salto = page.getByRole('link', { name: 'Saltar al contenido' })
  await salto.focus()
  await expect(salto).toBeInViewport()
  await page.keyboard.press('Enter')
  await expect(page.locator('#contenido')).toBeFocused()

  // Con Tab se llega a la ficha y Enter la abre; al cambiar de pantalla el foco va al contenido.
  const enlace = page.getByRole('link', { name: 'Ana María Gómez Rojas' })
  await enlace.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { level: 1, name: 'Ana María Gómez Rojas' })).toBeVisible()
  await expect(page.locator('#contenido')).toBeFocused()

  // El diálogo de revocar se abre con Enter y se cierra con Escape sin cambiar nada.
  await page.getByRole('button', { name: 'Revocar consentimiento' }).focus()
  await page.keyboard.press('Enter')
  const dialogo = page.getByRole('dialog')
  await expect(dialogo).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(dialogo).toBeHidden()
  await expect(page.getByRole('button', { name: 'Inscribir' })).toBeEnabled()
})

test('RF-09 · C2 · las secciones que aún no existen dicen «Próximamente»', async ({ page }) => {
  await entrar(page)
  const navegacion = page.getByRole('navigation', { name: 'Secciones' })
  // Inscripción y Cámaras llegaron el Día 2; Accesos, Asistencia y Horarios son del Día 3.
  for (const seccion of ['Accesos', 'Asistencia', 'Horarios']) {
    await navegacion.getByRole('link', { name: new RegExp(seccion) }).click()
    await expect(page.getByRole('heading', { level: 1, name: seccion })).toBeVisible()
    await expect(page.getByText('Esta pantalla está en construcción.')).toBeVisible()
  }
  await expect(navegacion.getByRole('link', { name: /Horarios/ })).toHaveAttribute('aria-current', 'page')
})
