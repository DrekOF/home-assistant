/**
 * Nombre: FichaPersona.tsx
 * Descripción: Ficha de la persona: sus datos, activar o desactivar, e «Inscribir», que solo se habilita con consentimiento vigente (RF-02 · C4).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { ArrowLeft, Pencil, ScanFace } from 'lucide-react'
import { useId } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { detalleDe, type Persona } from '../api/cliente'
import { useConsentimiento, useEditarPersona, useHorarios, usePersona } from '../api/consultas'
import { Aviso } from '../componentes/Aviso'
import { Boton, BotonEnlace } from '../componentes/Boton'
import { Esqueleto } from '../componentes/Esqueleto'
import { InsigniaEstado } from '../componentes/InsigniaEstado'
import { usarTitulo } from '../componentes/titulo'
import { formatearFechaHora } from '../logica/fechas'
import { resumirBloques } from '../logica/horarios'
import { PersonaNoDisponible } from './PersonaNoDisponible'
import { SeccionConsentimiento } from './SeccionConsentimiento'
import { NOMBRES_ROL } from './textos'

const AVISOS: Record<string, string> = {
  creada: 'Persona creada. Para inscribirla con la cámara, primero registra su consentimiento.',
  guardada: 'Cambios guardados.',
}

export function FichaPersona() {
  const { personaId = '' } = useParams()
  const persona = usePersona(personaId)
  usarTitulo(persona.data?.nombre ?? 'Persona')

  if (persona.isPending) {
    return (
      <div aria-busy="true">
        <p className="visualmente-oculto" role="status">
          Cargando la ficha…
        </p>
        <Esqueleto ancho="20rem" alto="2rem" />
      </div>
    )
  }
  if (persona.isError) {
    return <PersonaNoDisponible error={persona.error} reintentar={() => void persona.refetch()} />
  }
  return <Ficha persona={persona.data} />
}

function Ficha({ persona }: { persona: Persona }) {
  const consentimiento = useConsentimiento(persona.id)
  const horarios = useHorarios()
  const editar = useEditarPersona()
  const navegar = useNavigate()
  const { state } = useLocation() as { state: { aviso?: string } | null }
  const idMotivo = useId()

  const vigente = consentimiento.data != null
  const horario = horarios.data?.find((h) => h.id === persona.horario_id)
  const aviso = state?.aviso ? AVISOS[state.aviso] : undefined
  const motivo = consentimiento.isPending
    ? 'Revisando el consentimiento…'
    : vigente
      ? undefined
      : 'Para inscribir a esta persona, primero registra su consentimiento.'

  return (
    <>
      <Link className="miga" to="/personas">
        <ArrowLeft aria-hidden />
        Personas
      </Link>
      <div className="encabezado encabezado--arriba">
        <div className="encabezado__texto">
          <h1>{persona.nombre}</h1>
          <p className="encabezado__resumen">
            {NOMBRES_ROL[persona.rol]} · documento{' '}
            <span className="mono" translate="no">
              {persona.documento}
            </span>
          </p>
        </div>
        <div className="inscribir">
          <div className="botones">
            <BotonEnlace to={`/personas/${persona.id}/editar`} icono={Pencil}>
              Editar
            </BotonEnlace>
            <Boton
              variante="primario"
              icono={ScanFace}
              disabled={!vigente}
              aria-describedby={motivo ? idMotivo : undefined}
              onClick={() => navegar(`/inscripcion?persona=${persona.id}`)}
            >
              Inscribir
            </Boton>
          </div>
          {motivo && (
            <p id={idMotivo} className="inscribir__motivo">
              {motivo}
            </p>
          )}
        </div>
      </div>

      <div className="estado-accion" role="status">
        {aviso && <Aviso tono="ok">{aviso}</Aviso>}
        {editar.isError && <Aviso tono="error">No se pudo cambiar el estado: {detalleDe(editar.error)}</Aviso>}
      </div>

      <div className="ficha">
        <section className="panel seccion" aria-labelledby="titulo-datos">
          <div className="seccion__cabeza">
            <h2 id="titulo-datos">Datos</h2>
          </div>
          <dl className="datos">
            <dt>Estado</dt>
            <dd className="botones">
              {persona.activa ? (
                <InsigniaEstado tono="ok">Activa</InsigniaEstado>
              ) : (
                <InsigniaEstado tono="neutro">Inactiva</InsigniaEstado>
              )}
              <Boton
                variante="texto"
                cargando={editar.isPending}
                textoCargando="Guardando…"
                onClick={() => editar.mutate({ id: persona.id, cambios: { activa: !persona.activa } })}
              >
                {persona.activa ? 'Desactivar' : 'Activar'}
              </Boton>
            </dd>
            <dt>Documento</dt>
            <dd className="mono" translate="no">
              {persona.documento}
            </dd>
            <dt>Rol</dt>
            <dd>{NOMBRES_ROL[persona.rol]}</dd>
            <dt>Horario</dt>
            <dd>
              {persona.horario_nombre ?? 'Sin horario'}
              {horario && <div className="tabla__secundario">{resumirBloques(horario.bloques)}</div>}
            </dd>
            <dt>Huellas</dt>
            <dd className="numeros">
              {persona.muestras === 0
                ? 'Ninguna guardada'
                : persona.muestras === 1
                  ? '1 muestra guardada'
                  : `${persona.muestras} muestras guardadas`}
            </dd>
            <dt>Creada</dt>
            <dd>{formatearFechaHora(persona.creada)}</dd>
            <dt>Actualizada</dt>
            <dd>{formatearFechaHora(persona.actualizada)}</dd>
          </dl>
        </section>

        <SeccionConsentimiento persona={persona} consentimiento={consentimiento} />
      </div>
    </>
  )
}
