/**
 * Nombre: BarraAvance.tsx
 * Descripción: Barra de avance de la inscripción: un segmento por muestra, el conteo anunciado a los lectores de pantalla (RF-03 · C6) y un detalle opcional, como el tiempo que falta.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import type { CSSProperties, ReactNode } from 'react'

type PropsBarraAvance = {
  actual: number
  total?: number
  /** Va a la derecha del conteo y no se anuncia: el tiempo que falta cambia cada segundo. */
  detalle?: ReactNode
}

export function BarraAvance({ actual, total = 5, detalle }: PropsBarraAvance) {
  const hechas = Math.max(0, Math.min(actual, total))
  const estilo = { '--total': total } as CSSProperties
  return (
    <div className="avance">
      <div className="avance__cabeza">
        {/* Solo el conteo se anuncia, y solo cuando cambia. */}
        <span className="avance__etiqueta" aria-live="polite">
          Muestra {hechas} de {total}
        </span>
        {detalle && <span className="avance__detalle">{detalle}</span>}
      </div>
      <div
        className="avance__segmentos"
        style={estilo}
        role="progressbar"
        aria-label="Avance de la inscripción"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={hechas}
        aria-valuetext={`${hechas} de ${total} muestras`}
      >
        {Array.from({ length: total }, (_, indice) => (
          <span key={indice} className="avance__segmento" data-lleno={indice < hechas}>
            <span className="avance__relleno" />
          </span>
        ))}
      </div>
    </div>
  )
}
