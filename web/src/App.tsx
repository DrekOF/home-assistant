/**
 * Nombre: App.tsx
 * Descripción: Rutas de la web de AccesIA y cliente de TanStack Query, con el manejo común de la sesión vencida.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RotateCw } from 'lucide-react'
import { createBrowserRouter, Navigate } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { ErrorApi } from './api/cliente'
import { claves } from './api/consultas'
import { Aviso } from './componentes/Aviso'
import { Boton } from './componentes/Boton'
import { FichaPersona } from './pantallas/FichaPersona'
import { FormularioPersona } from './pantallas/FormularioPersona'
import { InicioSesion } from './pantallas/InicioSesion'
import { NoEncontrada } from './pantallas/NoEncontrada'
import { Personas } from './pantallas/Personas'
import { Proximamente } from './pantallas/Proximamente'
import { RequiereSesion } from './sesion'

/** Si la API dice que la sesión venció (401 sin_sesion), la web vuelve al inicio de sesión. */
function alFallar(error: Error) {
  if (error instanceof ErrorApi && error.codigo === 'sin_sesion') {
    cliente.setQueryData(claves.sesion, null)
  }
}

const cliente: QueryClient = new QueryClient({
  queryCache: new QueryCache({ onError: alFallar }),
  mutationCache: new MutationCache({ onError: alFallar }),
  defaultOptions: {
    queries: {
      // Un error del contrato (4xx) no se arregla reintentando; uno de red, a veces sí.
      retry: (intentos, error) => !(error instanceof ErrorApi && error.estado >= 400 && error.estado < 500) && intentos < 2,
      refetchOnWindowFocus: false,
    },
  },
})

function ErrorInesperado() {
  return (
    <div className="contenido">
      <Aviso
        tono="error"
        rol="alert"
        titulo="Algo salió mal en esta pantalla"
        accion={
          <Boton icono={RotateCw} onClick={() => window.location.reload()}>
            Recargar
          </Boton>
        }
      >
        Recarga la página. Si vuelve a pasar, anota qué estabas haciendo y avísale al equipo.
      </Aviso>
    </div>
  )
}

const enrutador = createBrowserRouter([
  { path: '/entrar', element: <InicioSesion />, errorElement: <ErrorInesperado /> },
  {
    element: <RequiereSesion />,
    errorElement: <ErrorInesperado />,
    children: [
      { index: true, element: <Navigate to="/personas" replace /> },
      { path: 'personas', element: <Personas /> },
      { path: 'personas/nueva', element: <FormularioPersona /> },
      { path: 'personas/:personaId', element: <FichaPersona /> },
      { path: 'personas/:personaId/editar', element: <FormularioPersona /> },
      { path: 'inscripcion', element: <Proximamente seccion="inscripcion" /> },
      { path: 'accesos', element: <Proximamente seccion="accesos" /> },
      { path: 'asistencia', element: <Proximamente seccion="asistencia" /> },
      { path: 'camaras', element: <Proximamente seccion="camaras" /> },
      { path: 'horarios', element: <Proximamente seccion="horarios" /> },
      { path: '*', element: <NoEncontrada /> },
    ],
  },
])

export function App() {
  return (
    <QueryClientProvider client={cliente}>
      <RouterProvider router={enrutador} />
    </QueryClientProvider>
  )
}
