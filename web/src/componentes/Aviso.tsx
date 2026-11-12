/**
 * Nombre: Aviso.tsx
 * Descripción: Aviso dentro de la página (información, éxito, advertencia o error), con título y acción opcionales.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { CircleCheck, CircleExclamationPoint, Info, TriangleExclamationPoint, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

type TonoAviso = 'info' | 'ok' | 'aviso' | 'error'

const ICONOS: Record<TonoAviso, LucideIcon> = {
  info: Info,
  ok: CircleCheck,
  aviso: TriangleExclamationPoint,
  error: CircleExclamationPoint,
}

type PropsAviso = {
  tono: TonoAviso
  titulo?: string
  children?: ReactNode
  accion?: ReactNode
  /** alert para errores que interrumpen; status para confirmaciones que se leen sin mover el foco. */
  rol?: 'alert' | 'status'
}

export function Aviso({ tono, titulo, children, accion, rol }: PropsAviso) {
  const Icono = ICONOS[tono]
  return (
    <div className={`aviso aviso--${tono}`} role={rol}>
      <Icono aria-hidden />
      <div className="aviso__cuerpo">
        {titulo && <p className="aviso__titulo">{titulo}</p>}
        {children && <div>{children}</div>}
      </div>
      {accion}
    </div>
  )
}
