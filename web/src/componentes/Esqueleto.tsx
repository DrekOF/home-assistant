/**
 * Nombre: Esqueleto.tsx
 * Descripción: Esqueletos de carga: una línea y filas de tabla, con un aviso solo para lectores de pantalla.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { CSSProperties } from 'react'

export function Esqueleto({ ancho = '100%', alto }: { ancho?: string; alto?: string }) {
  const estilo: CSSProperties = { width: ancho, height: alto }
  return <span className="esqueleto" style={estilo} aria-hidden />
}

/** Filas grises con el mismo alto de las reales, para que la tabla no salte al cargar. */
export function FilasEsqueleto({ filas, columnas }: { filas: number; columnas: number }) {
  const anchos = ['70%', '55%', '45%', '60%', '50%', '40%', '35%', '30%']
  return (
    <>
      {Array.from({ length: filas }, (_, fila) => (
        <tr key={fila} aria-hidden>
          {Array.from({ length: columnas }, (_, columna) => (
            <td key={columna}>
              <Esqueleto ancho={anchos[(fila + columna) % anchos.length]} />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}
