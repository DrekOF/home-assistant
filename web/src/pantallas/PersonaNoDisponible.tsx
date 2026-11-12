/**
 * Nombre: PersonaNoDisponible.tsx
 * Descripción: Lo que se ve cuando una persona no existe (404) o no se pudo cargar.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { ArrowLeft, RotateCw, UserX } from 'lucide-react'
import { detalleDe, ErrorApi } from '../api/cliente'
import { Aviso } from '../componentes/Aviso'
import { Boton, BotonEnlace } from '../componentes/Boton'
import { Vacio } from '../componentes/Vacio'

export function PersonaNoDisponible({ error, reintentar }: { error: unknown; reintentar: () => void }) {
  if (error instanceof ErrorApi && error.estado === 404) {
    return (
      <div className="panel">
        <Vacio
          icono={UserX}
          titulo="Esa persona no existe"
          acciones={
            <BotonEnlace to="/personas" icono={ArrowLeft}>
              Volver a Personas
            </BotonEnlace>
          }
        >
          Pudo ser borrada, o la dirección está incompleta. Búscala en la lista de personas.
        </Vacio>
      </div>
    )
  }
  return (
    <Aviso
      tono="error"
      rol="alert"
      titulo="No se pudo cargar la persona"
      accion={
        <Boton icono={RotateCw} onClick={reintentar}>
          Reintentar
        </Boton>
      }
    >
      {detalleDe(error)}
    </Aviso>
  )
}
