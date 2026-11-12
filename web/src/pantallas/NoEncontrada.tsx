/**
 * Nombre: NoEncontrada.tsx
 * Descripción: Pantalla para direcciones que no existen en la web.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { ArrowLeft, MapPinOff } from 'lucide-react'
import { BotonEnlace } from '../componentes/Boton'
import { usarTitulo } from '../componentes/titulo'
import { Vacio } from '../componentes/Vacio'

export function NoEncontrada() {
  usarTitulo('Página no encontrada')
  return (
    <>
      <h1 className="visualmente-oculto">Página no encontrada</h1>
      <div className="panel">
        <Vacio
          icono={MapPinOff}
          titulo="Esta página no existe"
          acciones={
            <BotonEnlace to="/personas" icono={ArrowLeft}>
              Ir a Personas
            </BotonEnlace>
          }
        >
          Revisa la dirección o vuelve a una sección del menú.
        </Vacio>
      </div>
    </>
  )
}
