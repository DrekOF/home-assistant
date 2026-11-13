/**
 * Nombre: Marco.tsx
 * Descripción: Marco de las pantallas con sesión: salto al contenido, barra lateral con la navegación, cinta del simulacro y cierre de sesión.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import { CalendarCheck, Cctv, Clock, DoorOpen, FlaskConical, LogOut, ScanFace, Users, type LucideIcon } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import type { Administrador } from '../api/cliente'
import { useCerrarSesion } from '../api/consultas'
import { Boton } from './Boton'
import { Marca } from './Marca'

type Seccion = { a: string; texto: string; icono: LucideIcon; pronto?: boolean }

export const SECCIONES: Seccion[] = [
  { a: '/personas', texto: 'Personas', icono: Users },
  { a: '/inscripcion', texto: 'Inscripción', icono: ScanFace },
  { a: '/accesos', texto: 'Accesos', icono: DoorOpen, pronto: true },
  { a: '/asistencia', texto: 'Asistencia', icono: CalendarCheck, pronto: true },
  { a: '/camaras', texto: 'Cámaras', icono: Cctv },
  { a: '/horarios', texto: 'Horarios', icono: Clock, pronto: true },
]

export function Marco({ administrador, children }: { administrador: Administrador; children: ReactNode }) {
  const contenido = useRef<HTMLElement>(null)
  const { pathname, state } = useLocation()
  const primeraVez = useRef(true)
  const navegar = useNavigate()
  const salir = useCerrarSesion()
  const desdeEntrada = (state as { desdeEntrada?: boolean } | null)?.desdeEntrada === true

  // Al cambiar de pantalla, el foco va al contenido: el lector de pantalla no se queda en el menú.
  // Recién entrado, también: el formulario de entrada ya no existe y el foco quedaría perdido.
  useEffect(() => {
    if (primeraVez.current) {
      primeraVez.current = false
      if (desdeEntrada) contenido.current?.focus({ preventScroll: true })
      return
    }
    contenido.current?.focus({ preventScroll: true })
    window.scrollTo({ top: 0 })
  }, [pathname])

  return (
    <div className="marco">
      <a className="salto" href="#contenido">
        Saltar al contenido
      </a>
      <aside className="lateral">
        <Link className="marca" to="/personas">
          <Marca />
          <span translate="no">AccesIA</span>
        </Link>
        <nav className="navegacion" aria-label="Secciones">
          <ul>
            {SECCIONES.map(({ a, texto, icono: Icono, pronto }) => (
              <li key={a}>
                <NavLink to={a}>
                  <Icono aria-hidden />
                  <span>{texto}</span>
                  {pronto && <span className="navegacion__pronto">pronto</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="lateral__pie">
          <p className="lateral__usuario">
            <strong>{administrador.nombre}</strong>
            <span>{administrador.correo}</span>
          </p>
          <Boton
            variante="texto"
            icono={LogOut}
            cargando={salir.isPending}
            textoCargando="Saliendo…"
            onClick={() => salir.mutate(undefined, { onSettled: () => navegar('/entrar', { replace: true }) })}
          >
            Cerrar sesión
          </Boton>
        </div>
      </aside>
      <div className="principal">
        {__SIMULACRO__ && (
          <p className="cinta-simulacro">
            <FlaskConical aria-hidden />
            <span>
              <strong>Simulacro:</strong> los datos son de ejemplo, viven en esta pestaña y vuelven a empezar al recargar.
            </span>
          </p>
        )}
        <main id="contenido" ref={contenido} tabIndex={-1} className="contenido">
          {children}
        </main>
      </div>
    </div>
  )
}
