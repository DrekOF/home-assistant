/**
 * Nombre: textos.ts
 * Descripción: Textos en español para los valores del contrato que se muestran en pantalla.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { Consentimiento, Rol } from '../api/cliente'

export const NOMBRES_ROL: Record<Rol, string> = {
  estudiante: 'Estudiante',
  docente: 'Docente',
  administrativo: 'Administrativo',
  otro: 'Otro',
}

export const ROLES = Object.keys(NOMBRES_ROL) as Rol[]

export const NOMBRES_MEDIO: Record<Consentimiento['medio'], string> = {
  web: 'En la web',
  papel: 'En papel',
}
