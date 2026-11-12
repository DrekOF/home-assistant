/**
 * Nombre: Personas.tsx
 * Descripción: Lista de personas con búsqueda, filtro por estado y paginación en la dirección; activar y desactivar con deshacer (RF-02 · C1).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { ChevronLeft, ChevronRight, RotateCw, Search, SearchX, UserPlus, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { detalleDe, type Persona } from '../api/cliente'
import { useEditarPersona, usePersonas } from '../api/consultas'
import { Aviso } from '../componentes/Aviso'
import { Boton, BotonEnlace } from '../componentes/Boton'
import { Campo } from '../componentes/Campo'
import { FilasEsqueleto } from '../componentes/Esqueleto'
import { InsigniaEstado } from '../componentes/InsigniaEstado'
import { usarTitulo } from '../componentes/titulo'
import { Vacio } from '../componentes/Vacio'
import { NOMBRES_ROL } from './textos'

const POR_PAGINA = 10
const COLUMNAS = 5

type FiltroEstado = 'todas' | 'activas' | 'inactivas'

function leerEstado(valor: string | null): FiltroEstado {
  return valor === 'activas' || valor === 'inactivas' ? valor : 'todas'
}

type Cambio = { persona: Persona; activa: boolean }

export function Personas() {
  usarTitulo('Personas')
  const [parametros, setParametros] = useSearchParams()
  const q = parametros.get('q') ?? ''
  const estado = leerEstado(parametros.get('estado'))
  const pagina = Math.max(1, Math.trunc(Number(parametros.get('pagina'))) || 1)
  const [busqueda, setBusqueda] = useState(q)
  const [cambio, setCambio] = useState<Cambio | null>(null)

  const consulta = usePersonas({
    q,
    activa: estado === 'todas' ? undefined : estado === 'activas',
    pagina,
    porPagina: POR_PAGINA,
  })
  const editar = useEditarPersona()

  /**
   * Cambia los filtros en la dirección: se pueden compartir y el botón Atrás los respeta.
   * Parte de la dirección de ese momento, no de la del último render: así la búsqueda que se
   * aplica con retraso no borra un filtro que se eligió mientras tanto.
   */
  function actualizar(cambios: Record<string, string | null>, reemplazar = false) {
    const nuevos = new URLSearchParams(window.location.search)
    for (const [clave, valor] of Object.entries(cambios)) {
      if (valor) nuevos.set(clave, valor)
      else nuevos.delete(clave)
    }
    setParametros(nuevos, { replace: reemplazar })
  }

  /** La dirección de otra página con los mismos filtros. */
  function enlacePagina(numero: number): string {
    const nuevos = new URLSearchParams(parametros)
    if (numero > 1) nuevos.set('pagina', String(numero))
    else nuevos.delete('pagina')
    const consulta = nuevos.toString()
    return consulta ? `/personas?${consulta}` : '/personas'
  }

  // La búsqueda se aplica cuando se deja de escribir un momento.
  useEffect(() => {
    const limpia = busqueda.trim()
    if (limpia === q) return
    const espera = window.setTimeout(() => actualizar({ q: limpia || null, pagina: null }, true), 250)
    return () => window.clearTimeout(espera)
  }, [busqueda, q])

  // Si la dirección cambia por fuera (Atrás), el campo la sigue.
  useEffect(() => {
    setBusqueda((actual) => (actual.trim() === q ? actual : q))
  }, [q])

  function cambiarActiva(persona: Persona, activa: boolean) {
    editar.mutate({ id: persona.id, cambios: { activa } }, { onSuccess: () => setCambio({ persona, activa }) })
  }

  const datos = consulta.data
  const total = datos?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))
  const hayFiltros = Boolean(q) || estado !== 'todas'
  const desde = total === 0 ? 0 : (pagina - 1) * POR_PAGINA + 1
  const hasta = Math.min(pagina * POR_PAGINA, total)

  return (
    <>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>Personas</h1>
          <p className="encabezado__resumen numeros">
            {datos ? (hayFiltros ? `${total} ${total === 1 ? 'resultado' : 'resultados'}` : `${total} personas registradas`) : 'Cargando…'}
          </p>
        </div>
        <BotonEnlace to="/personas/nueva" variante="primario" icono={UserPlus}>
          Nueva persona
        </BotonEnlace>
      </div>

      <div className="estado-accion" role="status">
        {cambio && (
          <Aviso
            tono="ok"
            accion={
              <Boton
                variante="texto"
                cargando={editar.isPending}
                textoCargando="Deshaciendo…"
                onClick={() =>
                  editar.mutate(
                    { id: cambio.persona.id, cambios: { activa: !cambio.activa } },
                    { onSuccess: () => setCambio(null) },
                  )
                }
              >
                Deshacer
              </Boton>
            }
          >
            {cambio.persona.nombre} quedó {cambio.activa ? 'activa' : 'inactiva'}.
          </Aviso>
        )}
        {editar.isError && (
          <Aviso tono="error">No se pudo cambiar el estado: {detalleDe(editar.error)}</Aviso>
        )}
      </div>

      <section className="panel" aria-labelledby="titulo-lista">
        <h2 id="titulo-lista" className="visualmente-oculto">
          Lista de personas
        </h2>
        <div className="herramientas" role="search">
          <Campo etiqueta="Buscar">
            {(control) => (
              <div className="buscador">
                <Search aria-hidden />
                <input
                  {...control}
                  className="control"
                  type="search"
                  name="q"
                  autoComplete="off"
                  spellCheck={false}
                  maxLength={60}
                  placeholder="Nombre o documento, sin importar tildes…"
                  value={busqueda}
                  onChange={(evento) => setBusqueda(evento.target.value)}
                />
              </div>
            )}
          </Campo>
          <Campo etiqueta="Estado">
            {(control) => (
              <select
                {...control}
                className="control"
                name="estado"
                value={estado}
                onChange={(evento) => actualizar({ estado: evento.target.value === 'todas' ? null : evento.target.value, pagina: null })}
              >
                <option value="todas">Todas</option>
                <option value="activas">Activas</option>
                <option value="inactivas">Inactivas</option>
              </select>
            )}
          </Campo>
        </div>

        {consulta.isError ? (
          <div className="seccion">
            <Aviso
              tono="error"
              rol="alert"
              titulo="No se pudo cargar la lista"
              accion={
                <Boton icono={RotateCw} onClick={() => void consulta.refetch()}>
                  Reintentar
                </Boton>
              }
            >
              {detalleDe(consulta.error)}
            </Aviso>
          </div>
        ) : datos && datos.elementos.length === 0 ? (
          hayFiltros ? (
            <Vacio
              icono={SearchX}
              titulo={q ? `Nadie coincide con «${q}»` : 'No hay personas con ese estado'}
              acciones={
                <Boton
                  onClick={() => {
                    setBusqueda('')
                    actualizar({ q: null, estado: null, pagina: null })
                  }}
                >
                  Quitar los filtros
                </Boton>
              }
            >
              Revisa la búsqueda o cambia el filtro de estado. Si la persona no está, créala.
            </Vacio>
          ) : (
            <Vacio
              icono={Users}
              titulo="Todavía no hay personas"
              acciones={
                <BotonEnlace to="/personas/nueva" variante="primario" icono={UserPlus}>
                  Nueva persona
                </BotonEnlace>
              }
            >
              Crea la primera persona. Después registras su consentimiento y la inscribes con la cámara.
            </Vacio>
          )
        ) : (
          <div className="panel--tabla">
            <table className="tabla" aria-busy={consulta.isFetching || undefined}>
              <thead>
                <tr>
                  <th scope="col">Nombre</th>
                  <th scope="col">Documento</th>
                  <th scope="col">Horario</th>
                  <th scope="col">Consentimiento</th>
                  <th scope="col" className="tabla__acciones">
                    <span className="visualmente-oculto">Acciones</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {!datos ? (
                  <FilasEsqueleto filas={6} columnas={COLUMNAS} />
                ) : (
                  datos.elementos.map((persona) => {
                    const cambiando = editar.isPending && editar.variables?.id === persona.id
                    return (
                      <tr key={persona.id}>
                        <td className="tabla__nombre">
                          <Link to={`/personas/${persona.id}`}>{persona.nombre}</Link>
                          <div className="tabla__secundario">
                            {NOMBRES_ROL[persona.rol]}
                            {!persona.activa && (
                              <>
                                {' · '}
                                <InsigniaEstado tono="neutro">Inactiva</InsigniaEstado>
                              </>
                            )}
                          </div>
                        </td>
                        <td className="mono" translate="no">
                          {persona.documento}
                        </td>
                        <td className={persona.horario_nombre ? undefined : 'tabla__secundario'}>
                          {persona.horario_nombre ?? 'Sin horario'}
                        </td>
                        <td>
                          {persona.consentimiento_vigente ? (
                            <InsigniaEstado tono="ok">Vigente</InsigniaEstado>
                          ) : (
                            <InsigniaEstado tono="neutro">Sin consentimiento</InsigniaEstado>
                          )}
                          {persona.consentimiento_vigente && (
                            <div className="tabla__secundario numeros">
                              {persona.muestras === 1 ? '1 muestra' : `${persona.muestras} muestras`}
                            </div>
                          )}
                        </td>
                        <td className="tabla__acciones">
                          <Boton
                            variante="texto"
                            cargando={cambiando}
                            textoCargando="Guardando…"
                            aria-label={`${persona.activa ? 'Desactivar' : 'Activar'} a ${persona.nombre}`}
                            onClick={() => cambiarActiva(persona, !persona.activa)}
                          >
                            {persona.activa ? 'Desactivar' : 'Activar'}
                          </Boton>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        )}

        {datos && total > 0 && (
          <nav className="paginacion" aria-label="Páginas de la lista">
            <p className="numeros">
              {desde}–{hasta} de {total} · página {pagina} de {paginas}
            </p>
            {/* Cambiar de página es navegar: son enlaces (se pueden abrir en otra pestaña). En los extremos, botones deshabilitados. */}
            <div className="botones">
              {pagina > 1 ? (
                <BotonEnlace to={enlacePagina(pagina - 1)} icono={ChevronLeft}>
                  Anterior
                </BotonEnlace>
              ) : (
                <Boton icono={ChevronLeft} disabled>
                  Anterior
                </Boton>
              )}
              {pagina < paginas ? (
                <BotonEnlace to={enlacePagina(pagina + 1)} iconoFinal={ChevronRight}>
                  Siguiente
                </BotonEnlace>
              ) : (
                <Boton iconoFinal={ChevronRight} disabled>
                  Siguiente
                </Boton>
              )}
            </div>
          </nav>
        )}
      </section>
    </>
  )
}
