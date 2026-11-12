/**
 * Nombre: sesion.tsx
 * Descripción: Puerta de las pantallas con sesión (RF-09 · C1): sin sesión lleva al inicio de sesión y vuelve después.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { RotateCw } from 'lucide-react'
import { Navigate, Outlet, useLocation } from 'react-router'
import { detalleDe } from './api/cliente'
import { useSesion } from './api/consultas'
import { Aviso } from './componentes/Aviso'
import { Boton } from './componentes/Boton'
import { Esqueleto } from './componentes/Esqueleto'
import { Marco } from './componentes/Marco'

/** Solo rutas internas: evita que «siguiente» lleve a otro sitio. */
export function destinoSeguro(siguiente: string | null): string {
  if (siguiente && siguiente.startsWith('/') && !siguiente.startsWith('//') && !siguiente.startsWith('/entrar')) {
    return siguiente
  }
  return '/personas'
}

export function RequiereSesion() {
  const sesion = useSesion()
  const ubicacion = useLocation()

  if (sesion.isPending) {
    return (
      <div className="contenido" aria-busy="true">
        <p className="visualmente-oculto" role="status">
          Cargando la sesión…
        </p>
        <Esqueleto ancho="12rem" alto="2rem" />
      </div>
    )
  }

  if (sesion.isError) {
    return (
      <div className="contenido">
        <Aviso
          tono="error"
          rol="alert"
          titulo="No se pudo revisar la sesión"
          accion={
            <Boton icono={RotateCw} onClick={() => void sesion.refetch()}>
              Reintentar
            </Boton>
          }
        >
          {detalleDe(sesion.error)}
        </Aviso>
      </div>
    )
  }

  if (!sesion.data) {
    const siguiente = encodeURIComponent(`${ubicacion.pathname}${ubicacion.search}`)
    return <Navigate to={`/entrar?siguiente=${siguiente}`} replace />
  }

  return (
    <Marco administrador={sesion.data}>
      <Outlet />
    </Marco>
  )
}
