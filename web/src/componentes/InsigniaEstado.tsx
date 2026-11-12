/**
 * Nombre: InsigniaEstado.tsx
 * Descripción: Insignia de estado con color, ícono y texto (nunca solo color).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { CircleCheck, CircleMinus, CircleX, TriangleExclamationPoint, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export type Tono = 'ok' | 'aviso' | 'error' | 'neutro'

const ICONOS: Record<Tono, LucideIcon> = {
  ok: CircleCheck,
  aviso: TriangleExclamationPoint,
  error: CircleX,
  neutro: CircleMinus,
}

export function InsigniaEstado({ tono, icono, children }: { tono: Tono; icono?: LucideIcon; children: ReactNode }) {
  const Icono = icono ?? ICONOS[tono]
  return (
    <span className={`insignia insignia--${tono}`}>
      <Icono aria-hidden />
      {children}
    </span>
  )
}
