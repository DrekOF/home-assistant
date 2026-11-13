/**
 * Nombre: playwright.servidor.config.ts
 * Descripción: Configuración de Playwright contra el servidor real (npm run e2e:servidor): sin simulacro, con /api hacia el puerto 8000 y las credenciales de infra/.env. Se corre a mano con Compose arriba.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

// Otro puerto que el de «npm run dev» (5173) y el de las pruebas con simulacro (5174).
const PUERTO = 5175
const ENV = fileURLToPath(new URL('../infra/.env', import.meta.url))

/**
 * Las credenciales del primer administrador salen de infra/.env, nunca del código (CLAUDE.md). Pasan a las
 * pruebas por variables de entorno del proceso y no se imprimen.
 */
function leerCredenciales(): void {
  if (!existsSync(ENV)) throw new Error('Falta infra/.env: créalo con .\\infra\\scripts\\generar-env.ps1')
  const valores = new Map<string, string>()
  for (const linea of readFileSync(ENV, 'utf8').split(/\r?\n/)) {
    const coincidencia = /^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/.exec(linea)
    if (coincidencia?.[1] && coincidencia[2] !== undefined) valores.set(coincidencia[1], coincidencia[2].replace(/^"(.*)"$/, '$1'))
  }
  const correo = valores.get('ADMIN_CORREO')
  const clave = valores.get('ADMIN_CLAVE_INICIAL')
  if (!correo || !clave) throw new Error('infra/.env no tiene ADMIN_CORREO y ADMIN_CLAVE_INICIAL')
  process.env.E2E_CORREO = correo
  process.env.E2E_CLAVE = clave
}

leerCredenciales()

export default defineConfig({
  testDir: 'e2e-servidor',
  outputDir: 'test-results/servidor',
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  // En orden: las pruebas comparten las personas de prueba que se crean al principio y se borran al final.
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report/servidor' }]],
  use: {
    baseURL: `http://localhost:${PUERTO}`,
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 720 } },
    },
  ],
  webServer: {
    // Sin --mode simulacro: la web habla con el servidor real por el proxy de Vite (/api → localhost:8000).
    command: `npm run dev -- --port ${PUERTO} --strictPort`,
    url: `http://localhost:${PUERTO}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
