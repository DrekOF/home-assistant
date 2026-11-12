/**
 * Nombre: titulo.ts
 * Descripción: Pone el título de la pestaña de cada pantalla («Personas · AccesIA»).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { useEffect } from 'react'

export function usarTitulo(titulo: string): void {
  useEffect(() => {
    document.title = `${titulo} · AccesIA`
  }, [titulo])
}
