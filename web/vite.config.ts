/**
 * Nombre: vite.config.ts
 * Descripción: Configuración de Vite y Vitest para la web de AccesIA: proxy de /api al servidor, modo simulacro y pruebas de la lógica.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

const web = fileURLToPath(new URL('.', import.meta.url))
// El simulacro y las pruebas leen specs/consentimiento.md, que está fuera de web/.
const specs = fileURLToPath(new URL('../specs', import.meta.url))

export default defineConfig(({ mode }) => {
  // VITE_SIMULACRO=1 sale de .env.simulacro (npm run dev:simulacro) o de la variable de entorno.
  const simulacro = loadEnv(mode, web, 'VITE_').VITE_SIMULACRO === '1'
  return {
    plugins: [react()],
    // Constante de compilación: sin simulacro, su código se elimina del paquete.
    define: { __SIMULACRO__: JSON.stringify(simulacro) },
    server: {
      port: 5173,
      strictPort: true,
      // En desarrollo, la API la atiende el servidor (tarea B) en el puerto 8000.
      proxy: { '/api': 'http://localhost:8000' },
      fs: { allow: [web, specs] },
    },
    preview: { port: 4173, strictPort: true },
    test: {
      include: ['src/**/*.test.ts'],
      environment: 'node',
    },
  }
})
