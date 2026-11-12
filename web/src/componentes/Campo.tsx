/**
 * Nombre: Campo.tsx
 * Descripción: Campo de formulario con etiqueta visible, ayuda y error unidos al control por aria-describedby.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { CircleExclamationPoint } from 'lucide-react'
import { useId, type ReactNode } from 'react'
import { clases } from './clases'

export type PropsControl = {
  id: string
  'aria-describedby'?: string
  'aria-invalid'?: true
}

type PropsCampo = {
  etiqueta: string
  ayuda?: ReactNode
  error?: string
  opcional?: boolean
  className?: string
  /** Recibe el id y los atributos de accesibilidad que debe llevar el control. */
  children: (control: PropsControl) => ReactNode
}

export function Campo({ etiqueta, ayuda, error, opcional = false, className, children }: PropsCampo) {
  const id = useId()
  const idAyuda = ayuda ? `${id}-ayuda` : undefined
  const idError = error ? `${id}-error` : undefined
  const describe = [idError, idAyuda].filter(Boolean).join(' ') || undefined
  return (
    <div className={clases('campo', className)}>
      <label className="campo__etiqueta" htmlFor={id}>
        {etiqueta}
        {opcional && <span className="campo__opcional"> (opcional)</span>}
      </label>
      {children({ id, 'aria-describedby': describe, 'aria-invalid': error ? true : undefined })}
      {error && (
        <p className="campo__error" id={idError}>
          <CircleExclamationPoint aria-hidden />
          {error}
        </p>
      )}
      {ayuda && (
        <p className="campo__ayuda" id={idAyuda}>
          {ayuda}
        </p>
      )}
    </div>
  )
}

/** Lleva el foco al primer control con error, como piden las guías de formularios. */
export function enfocarPrimerError(formulario: HTMLElement | null): void {
  requestAnimationFrame(() => {
    formulario?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
  })
}
