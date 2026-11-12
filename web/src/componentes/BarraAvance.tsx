/**
 * Nombre: BarraAvance.tsx
 * Descripción: Barra de avance de la inscripción: un segmento por muestra y el conteo anunciado a los lectores de pantalla (RF-03 · C6).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { CSSProperties } from 'react'

export function BarraAvance({ actual, total = 5 }: { actual: number; total?: number }) {
  const hechas = Math.max(0, Math.min(actual, total))
  const estilo = { '--total': total } as CSSProperties
  return (
    <div className="avance">
      <div className="avance__cabeza">
        <span className="avance__etiqueta" aria-live="polite">
          Muestra {hechas} de {total}
        </span>
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
