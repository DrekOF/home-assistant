/**
 * Nombre: navegador.ts
 * Descripción: Arranca el simulacro de la API en el navegador con el service worker de MSW.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { setupWorker } from 'msw/browser'
import { manejadores } from './manejadores'

export async function iniciarSimulacro(): Promise<void> {
  const trabajador = setupWorker(...manejadores)
  await trabajador.start({
    quiet: true,
    // Lo que no es de la API (la propia web, las fuentes) sigue su camino normal.
    onUnhandledFrame({ frame, defaults }) {
      if (frame.protocol !== 'http') return
      const { request } = frame.data as { request: Request }
      if (new URL(request.url).pathname.startsWith('/api/')) defaults.error()
    },
  })
}
