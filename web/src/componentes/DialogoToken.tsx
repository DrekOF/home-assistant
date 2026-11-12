/**
 * Nombre: DialogoToken.tsx
 * Descripción: Muestra una sola vez el token de una cámara, con botón para copiarlo y cómo usarlo (RF-10 · C1 y C2). Al cerrarse, el token se olvida.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { Check, Copy, KeyRound } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Boton } from './Boton'

type PropsDialogoToken = {
  /** Nombre de la cámara, para el título. */
  nombre: string
  token: string
  /** Si es el token de una cámara recién creada o el que reemplaza a uno anterior. */
  motivo: 'creada' | 'cambiado'
  onCerrar: () => void
}

type Copia = 'pendiente' | 'copiado' | 'a-mano'

/**
 * El token vive solo en el estado de quien abre este diálogo: no va a la dirección, ni al almacenamiento del
 * navegador, ni al caché de TanStack Query. Quien lo abre lo borra al cerrarlo.
 */
export function DialogoToken({ nombre, token, motivo, onCerrar }: PropsDialogoToken) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const campo = useRef<HTMLInputElement>(null)
  const idTitulo = useId()
  const idTexto = useId()
  const idCampo = useId()
  const [copia, setCopia] = useState<Copia>('pendiente')

  useEffect(() => {
    const elemento = dialogo.current
    if (elemento && !elemento.open) elemento.showModal()
    // Queda seleccionado: también se puede copiar con Ctrl+C.
    campo.current?.focus()
    campo.current?.select()
  }, [])

  async function copiar() {
    try {
      // Fuera de localhost o https, el navegador no deja usar el portapapeles.
      if (!navigator.clipboard) throw new Error('Sin portapapeles')
      await navigator.clipboard.writeText(token)
      setCopia('copiado')
    } catch {
      campo.current?.focus()
      campo.current?.select()
      setCopia('a-mano')
    }
  }

  return (
    <dialog
      ref={dialogo}
      className="dialogo"
      aria-labelledby={idTitulo}
      aria-describedby={idTexto}
      onCancel={(evento) => {
        evento.preventDefault()
        onCerrar()
      }}
    >
      <div className="dialogo__cuerpo">
        <KeyRound aria-hidden className="dialogo__icono dialogo__icono--acento" />
        <h2 id={idTitulo}>Token de la cámara {nombre}</h2>
        <div id={idTexto} className="dialogo__texto">
          <p>
            {motivo === 'cambiado' && 'El token anterior ya no sirve. '}
            <strong>Cópialo ahora: no se vuelve a mostrar.</strong> Si se pierde, cambia el token.
          </p>
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor={idCampo}>
            Token
          </label>
          <div className="token">
            <input
              ref={campo}
              id={idCampo}
              name="token"
              className="control mono token__valor"
              readOnly
              value={token}
              autoComplete="off"
              spellCheck={false}
              translate="no"
              onFocus={(evento) => evento.currentTarget.select()}
            />
            <Boton icono={copia === 'copiado' ? Check : Copy} onClick={() => void copiar()}>
              {copia === 'copiado' ? 'Copiado' : 'Copiar'}
            </Boton>
          </div>
          <p className="campo__ayuda" role="status">
            {copia === 'copiado' && 'Quedó en el portapapeles.'}
            {copia === 'a-mano' && 'El navegador no dejó copiarlo: quedó seleccionado, cópialo con Ctrl+C.'}
          </p>
        </div>
        <div className="token__usos">
          <h3>Dónde ponerlo</h3>
          <dl className="datos">
            <dt>Consola de la cámara</dt>
            <dd>
              <code translate="no">token &lt;token&gt;</code>
            </dd>
            <dt>Simulador, en PowerShell</dt>
            <dd>
              <code translate="no">$env:TOKEN_CAMARA = "&lt;token&gt;"</code>
            </dd>
          </dl>
        </div>
      </div>
      <div className="dialogo__pie">
        <Boton variante="primario" onClick={onCerrar}>
          Ya lo copié
        </Boton>
      </div>
    </dialog>
  )
}
