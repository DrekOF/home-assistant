/**
 * Nombre: Vacio.tsx
 * Descripción: Estado vacío que dice qué pasa y qué hacer a continuación.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

type PropsVacio = { icono: LucideIcon; titulo: string; children: ReactNode; acciones?: ReactNode }

export function Vacio({ icono: Icono, titulo, children, acciones }: PropsVacio) {
  return (
    <div className="vacio">
      <Icono aria-hidden className="vacio__icono" />
      <p className="aviso__titulo">{titulo}</p>
      <p className="vacio__texto">{children}</p>
      {acciones && <div className="botones">{acciones}</div>}
    </div>
  )
}
