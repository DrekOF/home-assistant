/**
 * Nombre: ahora.ts
 * Descripción: La hora actual que avanza cada segundo, para contar el tiempo que falta hasta que vence una inscripción (R9).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { useEffect, useState } from 'react'

/** Date.now() que se actualiza cada segundo mientras `activo`; quieto cuando no hay nada que contar. */
export function usarAhora(activo = true): number {
  const [ahora, setAhora] = useState(() => Date.now())
  useEffect(() => {
    if (!activo) return
    setAhora(Date.now())
    const intervalo = window.setInterval(() => setAhora(Date.now()), 1000)
    return () => window.clearInterval(intervalo)
  }, [activo])
  return ahora
}
