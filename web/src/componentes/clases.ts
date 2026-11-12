/**
 * Nombre: clases.ts
 * Descripción: Une nombres de clases CSS y descarta los vacíos.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

export function clases(...nombres: Array<string | false | null | undefined>): string {
  return nombres.filter(Boolean).join(' ')
}
