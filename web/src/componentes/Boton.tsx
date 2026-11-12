/**
 * Nombre: Boton.tsx
 * Descripción: Botón y enlace con forma de botón: variantes, ícono al inicio o al final y estado de carga con texto.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { LoaderCircle, type LucideIcon } from 'lucide-react'
import type { ComponentProps, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router'
import { clases } from './clases'

export type VarianteBoton = 'primario' | 'secundario' | 'peligro' | 'peligro-suave' | 'texto'

type Iconos = {
  /** Ícono antes del texto. */
  icono?: LucideIcon
  /** Ícono después del texto, como la flecha de «Siguiente». */
  iconoFinal?: LucideIcon
}

type PropsBoton = ComponentProps<'button'> &
  Iconos & {
    variante?: VarianteBoton
    /** Mientras la petición corre, el botón gira y dice qué hace («Guardando…»). */
    cargando?: boolean
    textoCargando?: string
    children: ReactNode
  }

export function Boton({
  variante = 'secundario',
  icono: Icono,
  iconoFinal: IconoFinal,
  cargando = false,
  textoCargando,
  children,
  className,
  type = 'button',
  disabled,
  ...resto
}: PropsBoton) {
  return (
    <button
      type={type}
      className={clases('boton', `boton--${variante}`, className)}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      {...resto}
    >
      {cargando ? <LoaderCircle aria-hidden className="boton__giro" /> : Icono ? <Icono aria-hidden /> : null}
      <span>{cargando && textoCargando ? textoCargando : children}</span>
      {IconoFinal && !cargando ? <IconoFinal aria-hidden /> : null}
    </button>
  )
}

type PropsEnlace = LinkProps & Iconos & { variante?: VarianteBoton; children: ReactNode }

/** Para navegar: es un enlace (se puede abrir en otra pestaña), con aspecto de botón. */
export function BotonEnlace({
  variante = 'secundario',
  icono: Icono,
  iconoFinal: IconoFinal,
  children,
  className,
  ...resto
}: PropsEnlace) {
  return (
    <Link className={clases('boton', `boton--${variante}`, className)} {...resto}>
      {Icono ? <Icono aria-hidden /> : null}
      <span>{children}</span>
      {IconoFinal ? <IconoFinal aria-hidden /> : null}
    </Link>
  )
}
