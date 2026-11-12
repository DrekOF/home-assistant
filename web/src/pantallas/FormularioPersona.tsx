/**
 * Nombre: FormularioPersona.tsx
 * Descripción: Formulario para crear o editar una persona, con el horario elegido de la lista y el resumen de sus bloques (RF-02 · C1, D-20).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { ArrowLeft, Save, UserPlus } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useBlocker, useNavigate, useParams } from 'react-router'
import { detalleDe, ErrorApi, type Persona, type PersonaCambios, type Rol } from '../api/cliente'
import { useCrearPersona, useEditarPersona, useHorarios, usePersona } from '../api/consultas'
import { Aviso } from '../componentes/Aviso'
import { Boton } from '../componentes/Boton'
import { Campo, enfocarPrimerError } from '../componentes/Campo'
import { DialogoConfirmacion } from '../componentes/DialogoConfirmacion'
import { Esqueleto } from '../componentes/Esqueleto'
import { usarTitulo } from '../componentes/titulo'
import { resumirBloques } from '../logica/horarios'
import { hayErrores, limpiarNombre, NOMBRE_MAX, validarPersona, type Errores } from '../logica/validaciones'
import { PersonaNoDisponible } from './PersonaNoDisponible'
import { NOMBRES_ROL, ROLES } from './textos'

export function FormularioPersona() {
  const { personaId } = useParams()
  const persona = usePersona(personaId)
  usarTitulo(personaId ? 'Editar persona' : 'Nueva persona')

  if (personaId && persona.isPending) {
    return (
      <div aria-busy="true">
        <p className="visualmente-oculto" role="status">
          Cargando la persona…
        </p>
        <Esqueleto ancho="16rem" alto="2rem" />
      </div>
    )
  }
  if (personaId && persona.isError) {
    return <PersonaNoDisponible error={persona.error} reintentar={() => void persona.refetch()} />
  }
  return <Formulario key={personaId ?? 'nueva'} persona={personaId ? persona.data : undefined} />
}

type Valores = { nombre: string; documento: string; rol: Rol; horarioId: string; activa: boolean }

function valoresDe(persona?: Persona): Valores {
  return {
    nombre: persona?.nombre ?? '',
    documento: persona?.documento ?? '',
    rol: persona?.rol ?? 'estudiante',
    horarioId: persona?.horario_id ?? '',
    activa: persona?.activa ?? true,
  }
}

/** Solo lo que cambió: PATCH pide al menos un dato (minProperties: 1). */
function soloCambios(persona: Persona, datos: Required<PersonaCambios>): PersonaCambios {
  const cambios: PersonaCambios = {}
  if (datos.nombre !== persona.nombre) cambios.nombre = datos.nombre
  if (datos.documento !== persona.documento) cambios.documento = datos.documento
  if (datos.rol !== persona.rol) cambios.rol = datos.rol
  if (datos.horario_id !== persona.horario_id) cambios.horario_id = datos.horario_id
  if (datos.activa !== persona.activa) cambios.activa = datos.activa
  return cambios
}

function Formulario({ persona }: { persona?: Persona }) {
  const inicial = valoresDe(persona)
  const [valores, setValores] = useState(inicial)
  const [errores, setErrores] = useState<Errores<'nombre' | 'documento'>>({})
  const horarios = useHorarios()
  const crear = useCrearPersona()
  const editar = useEditarPersona()
  const navegar = useNavigate()
  const formulario = useRef<HTMLFormElement>(null)
  const guardado = useRef(false)
  const mutacion = persona ? editar : crear
  const sucio = JSON.stringify(valores) !== JSON.stringify(inicial)
  const volver = persona ? `/personas/${persona.id}` : '/personas'

  // Antes de salir con cambios sin guardar, se pregunta (dentro de la web y al cerrar la pestaña).
  const bloqueo = useBlocker(
    ({ currentLocation, nextLocation }) =>
      sucio && !guardado.current && currentLocation.pathname !== nextLocation.pathname,
  )
  useEffect(() => {
    if (!sucio) return
    const avisar = (evento: BeforeUnloadEvent) => evento.preventDefault()
    window.addEventListener('beforeunload', avisar)
    return () => window.removeEventListener('beforeunload', avisar)
  }, [sucio])

  function cambiar<Clave extends keyof Valores>(clave: Clave, valor: Valores[Clave]) {
    setValores((actuales) => ({ ...actuales, [clave]: valor }))
  }

  function alGuardar(guardada: Persona) {
    guardado.current = true
    navegar(`/personas/${guardada.id}`, { state: { aviso: persona ? 'guardada' : 'creada' } })
  }

  function alFallar(error: Error) {
    if (error instanceof ErrorApi && error.codigo === 'documento_duplicado') {
      setErrores({ documento: error.message })
      enfocarPrimerError(formulario.current)
    }
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const encontrados = validarPersona(valores)
    setErrores(encontrados)
    if (hayErrores(encontrados)) {
      enfocarPrimerError(formulario.current)
      return
    }
    const datos = {
      nombre: limpiarNombre(valores.nombre),
      documento: valores.documento.trim(),
      rol: valores.rol,
      horario_id: valores.horarioId || null,
      activa: valores.activa,
    }
    if (!persona) {
      crear.mutate(datos, { onSuccess: alGuardar, onError: alFallar })
      return
    }
    const cambios = soloCambios(persona, datos)
    if (Object.keys(cambios).length === 0) {
      guardado.current = true
      navegar(volver)
      return
    }
    editar.mutate({ id: persona.id, cambios }, { onSuccess: alGuardar, onError: alFallar })
  }

  const elegido = horarios.data?.find((horario) => horario.id === valores.horarioId)
  const ayudaHorario = horarios.isError
    ? 'No se pudieron cargar los horarios. Puedes guardar sin horario y elegirlo después.'
    : elegido
      ? resumirBloques(elegido.bloques)
      : 'Sin horario, sus llegadas no se califican como a tiempo o tarde.'
  const errorGeneral =
    mutacion.isError && !(mutacion.error instanceof ErrorApi && mutacion.error.codigo === 'documento_duplicado')

  return (
    <>
      <Link className="miga" to={volver}>
        <ArrowLeft aria-hidden />
        {persona ? persona.nombre : 'Personas'}
      </Link>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>{persona ? 'Editar persona' : 'Nueva persona'}</h1>
          <p className="encabezado__resumen">
            {persona
              ? 'Los cambios se guardan cuando los confirmas.'
              : 'Después de crearla, registras su consentimiento y la inscribes.'}
          </p>
        </div>
      </div>

      <form ref={formulario} className="formulario" onSubmit={enviar} noValidate>
        {errorGeneral && (
          <Aviso tono="error" rol="alert" titulo="No se pudo guardar">
            {detalleDe(mutacion.error)}
          </Aviso>
        )}
        <div className="panel formulario__rejilla">
          <Campo etiqueta="Nombre completo" error={errores.nombre} className="campo--ancho">
            {(control) => (
              <input
                {...control}
                className="control"
                name="nombre"
                autoComplete="off"
                spellCheck={false}
                maxLength={NOMBRE_MAX}
                placeholder="Ana María Gómez Rojas…"
                value={valores.nombre}
                onChange={(evento) => cambiar('nombre', evento.target.value)}
              />
            )}
          </Campo>
          <Campo
            etiqueta="Documento"
            error={errores.documento}
            ayuda="Letras, números o guiones, sin puntos ni espacios."
          >
            {(control) => (
              <input
                {...control}
                className="control mono"
                name="documento"
                autoComplete="off"
                spellCheck={false}
                maxLength={20}
                placeholder="1075234567…"
                value={valores.documento}
                onChange={(evento) => cambiar('documento', evento.target.value)}
              />
            )}
          </Campo>
          <Campo etiqueta="Rol">
            {(control) => (
              <select
                {...control}
                className="control"
                name="rol"
                value={valores.rol}
                onChange={(evento) => cambiar('rol', evento.target.value as Rol)}
              >
                {ROLES.map((rol) => (
                  <option key={rol} value={rol}>
                    {NOMBRES_ROL[rol]}
                  </option>
                ))}
              </select>
            )}
          </Campo>
          <Campo etiqueta="Horario" ayuda={ayudaHorario} className="campo--ancho">
            {(control) => (
              <select
                {...control}
                className="control"
                name="horario"
                disabled={horarios.isPending}
                value={valores.horarioId}
                onChange={(evento) => cambiar('horarioId', evento.target.value)}
              >
                <option value="">{horarios.isPending ? 'Cargando horarios…' : 'Sin horario'}</option>
                {horarios.data?.map((horario) => (
                  <option key={horario.id} value={horario.id}>
                    {horario.nombre}
                  </option>
                ))}
              </select>
            )}
          </Campo>
          <label className="opcion campo--ancho">
            <input
              type="checkbox"
              name="activa"
              checked={valores.activa}
              onChange={(evento) => cambiar('activa', evento.target.checked)}
            />
            <span className="opcion__texto">
              <span>Persona activa</span>
              <span className="opcion__detalle">
                Si está inactiva, la puerta no se abre para ella aunque la cámara la reconozca.
              </span>
            </span>
          </label>
        </div>
        <div className="formulario__pie">
          <Boton
            type="submit"
            variante="primario"
            icono={persona ? Save : UserPlus}
            cargando={mutacion.isPending}
            textoCargando="Guardando…"
          >
            {persona ? 'Guardar cambios' : 'Crear persona'}
          </Boton>
          <Link to={volver}>Cancelar</Link>
        </div>
      </form>

      <DialogoConfirmacion
        abierto={bloqueo.state === 'blocked'}
        titulo="¿Salir sin guardar?"
        textoConfirmar="Salir sin guardar"
        textoCargando="Saliendo…"
        textoCancelar="Seguir editando"
        onConfirmar={() => bloqueo.proceed?.()}
        onCerrar={() => bloqueo.reset?.()}
      >
        <p>Los cambios de este formulario todavía no se han guardado y se perderán.</p>
      </DialogoConfirmacion>
    </>
  )
}
