/**
 * Nombre: DialogoConfirmacion.tsx
 * Descripción: Confirmación de una acción que no se puede deshacer, con el <dialog> nativo del navegador.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { TriangleExclamationPoint } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { Aviso } from './Aviso'
import { Boton } from './Boton'

type PropsDialogo = {
  abierto: boolean
  titulo: string
  children: ReactNode
  textoConfirmar: string
  textoCargando: string
  textoCancelar?: string
  ocupado?: boolean
  error?: string
  onConfirmar: () => void
  onCerrar: () => void
}

export function DialogoConfirmacion({
  abierto,
  titulo,
  children,
  textoConfirmar,
  textoCargando,
  textoCancelar = 'Cancelar',
  ocupado = false,
  error,
  onConfirmar,
  onCerrar,
}: PropsDialogo) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const cancelar = useRef<HTMLButtonElement>(null)
  const idTitulo = useId()
  const idTexto = useId()

  useEffect(() => {
    const elemento = dialogo.current
    if (!elemento) return
    if (abierto && !elemento.open) {
      elemento.showModal()
      // Lo seguro primero: el foco empieza en Cancelar.
      cancelar.current?.focus()
    } else if (!abierto && elemento.open) {
      elemento.close()
    }
  }, [abierto])

  return (
    <dialog
      ref={dialogo}
      className="dialogo"
      aria-labelledby={idTitulo}
      aria-describedby={idTexto}
      onCancel={(evento) => {
        // Escape cierra, salvo mientras la acción está en curso.
        evento.preventDefault()
        if (!ocupado) onCerrar()
      }}
    >
      <div className="dialogo__cuerpo">
        <TriangleExclamationPoint aria-hidden className="dialogo__icono" />
        <h2 id={idTitulo}>{titulo}</h2>
        <div id={idTexto} className="dialogo__texto">
          {children}
        </div>
        {error && (
          <Aviso tono="error" rol="alert">
            {error}
          </Aviso>
        )}
      </div>
      <div className="dialogo__pie">
        <Boton ref={cancelar} variante="secundario" onClick={onCerrar} disabled={ocupado}>
          {textoCancelar}
        </Boton>
        <Boton variante="peligro" onClick={onConfirmar} cargando={ocupado} textoCargando={textoCargando}>
          {textoConfirmar}
        </Boton>
      </div>
    </dialog>
  )
}
