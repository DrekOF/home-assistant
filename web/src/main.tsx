/**
 * Nombre: main.tsx
 * Descripción: Punto de entrada de la web de AccesIA: fuentes, estilos, simulacro opcional y montaje de React.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import '@fontsource-variable/atkinson-hyperlegible-next'
import '@fontsource-variable/atkinson-hyperlegible-mono'
import './estilos/tokens.css'
import './estilos/base.css'
import './estilos/componentes.css'
import './estilos/marco.css'
import './estilos/pantallas.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'

async function arrancar() {
  // Con VITE_SIMULACRO=1, MSW responde la API dentro del navegador (npm run dev:simulacro).
  if (__SIMULACRO__) {
    const { iniciarSimulacro } = await import('./simulacro/navegador')
    await iniciarSimulacro()
  }
  const raiz = document.getElementById('raiz')
  if (!raiz) throw new Error('Falta el elemento #raiz en index.html')
  createRoot(raiz).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void arrancar()
