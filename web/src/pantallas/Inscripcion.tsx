/**
 * Nombre: Inscripcion.tsx
 * Descripción: Abrir una inscripción para una persona con consentimiento vigente y una cámara activa; ante un 409, ver o cancelar la que ya estaba; y las inscripciones en curso (RF-03 · C1 y C5, R9).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { Cctv, ScanFace, UserRound, Users } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { detalleDe, ErrorApi, type Dispositivo, type InscripcionNueva, type Persona } from '../api/cliente'
import {
  useAbrirInscripcion,
  useCamara,
  useCamaras,
  useCancelarInscripcion,
  useInscripcion,
  usePersona,
  usePersonasConConsentimiento,
} from '../api/consultas'
import { usarAhora } from '../componentes/ahora'
import { Aviso } from '../componentes/Aviso'
import { Boton, BotonEnlace } from '../componentes/Boton'
import { Campo, enfocarPrimerError } from '../componentes/Campo'
import { DialogoConfirmacion } from '../componentes/DialogoConfirmacion'
import { usarTitulo } from '../componentes/titulo'
import { contarMuestras, formatearRestante, restanteHasta } from '../logica/inscripcion'
import { hayErrores, type Errores } from '../logica/validaciones'

type Problema = { titulo: string; texto: string; enlace?: { a: string; texto: string } }

function textoPersona(persona: Persona): string {
  return [persona.nombre, !persona.activa && 'inactiva', contarMuestras(persona.muestras)].filter(Boolean).join(' · ')
}

function textoCamara(camara: Dispositivo): string {
  return [
    `${camara.nombre} (${camara.codigo})`,
    camara.inscripcion_activa && 'inscribiendo',
    !camara.en_linea && 'sin conexión',
  ]
    .filter(Boolean)
    .join(' · ')
}

export function Inscripcion() {
  usarTitulo('Inscripción')
  // La persona y la cámara elegidas viven en la dirección: se pueden enlazar y Atrás las respeta.
  const [parametros, setParametros] = useSearchParams()
  const elegidaPersona = parametros.get('persona') ?? ''
  const elegida = parametros.get('camara') ?? ''
  const personas = usePersonasConConsentimiento()
  const camaras = useCamaras()
  const activas = camaras.data?.filter((camara) => camara.activo) ?? []
  const enCurso = camaras.data?.filter((camara) => camara.inscripcion_activa) ?? []

  // Solo vale si está en la lista: la de la dirección puede no tener consentimiento vigente.
  const personaId = personas.data?.some((p) => p.id === elegidaPersona) ? elegidaPersona : ''
  // Con una sola cámara activa, ya queda elegida.
  const codigo = elegida || (activas.length === 1 ? (activas[0]?.codigo ?? '') : '')
  const camara = activas.find((c) => c.codigo === codigo)

  const [errores, setErrores] = useState<Errores<'persona' | 'camara'>>({})
  const [problema, setProblema] = useState<Problema>()
  const [ocupada, setOcupada] = useState<string>()
  const abrir = useAbrirInscripcion()
  const navegar = useNavigate()
  const formulario = useRef<HTMLFormElement>(null)

  // La persona de la dirección (desde «Inscribir» en su ficha) no está en la lista: no tiene consentimiento vigente.
  const pedidaSinConsentimiento =
    Boolean(elegidaPersona) && personas.data !== undefined && !personas.data.some((p) => p.id === elegidaPersona)
  const pedida = usePersona(pedidaSinConsentimiento ? elegidaPersona : undefined)

  function recordar(clave: 'persona' | 'camara', valor: string) {
    const nuevos = new URLSearchParams(window.location.search)
    if (valor) nuevos.set(clave, valor)
    else nuevos.delete(clave)
    setParametros(nuevos, { replace: true })
  }

  function abrirCon(datos: InscripcionNueva) {
    setProblema(undefined)
    abrir.mutate(datos, {
      onSuccess: (inscripcion) => navegar(`/inscripcion/${inscripcion.id}`),
      onError: (error) => {
        if (!(error instanceof ErrorApi)) {
          setProblema({ titulo: 'No se pudo abrir la inscripción', texto: detalleDe(error) })
          return
        }
        if (error.codigo === 'inscripcion_activa') {
          setOcupada(datos.dispositivo)
          return
        }
        // La lista estaba vieja (consentimiento revocado, cámara desactivada o borrada): se vuelve a pedir.
        void personas.refetch()
        void camaras.refetch()
        if (error.codigo === 'sin_consentimiento') {
          setProblema({
            titulo: 'Esta persona no tiene consentimiento vigente',
            texto: error.message,
            enlace: { a: `/personas/${datos.persona_id}`, texto: 'Ir a su ficha' },
          })
          return
        }
        setProblema({ titulo: 'No se pudo abrir la inscripción', texto: error.message })
      },
    })
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const encontrados: Errores<'persona' | 'camara'> = {}
    if (!personaId) encontrados.persona = 'Elige a la persona que se inscribe.'
    if (!codigo) encontrados.camara = 'Elige la cámara.'
    setErrores(encontrados)
    if (hayErrores(encontrados)) {
      enfocarPrimerError(formulario.current)
      return
    }
    abrirCon({ persona_id: personaId, dispositivo: codigo })
  }

  const sinPersonas = personas.data?.length === 0
  const sinCamaras = camaras.data !== undefined && activas.length === 0
  const ayudaCamara =
    camara && !camara.en_linea
      ? `${camara.nombre} está sin conexión: no llegarán muestras hasta que se conecte.`
      : 'Solo aparecen las cámaras activas.'

  return (
    <>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>Inscripción</h1>
          <p className="encabezado__resumen">
            Inscribe a una persona con la cámara: cada cara válida se guarda como una muestra.
          </p>
        </div>
      </div>

      <div className="inscripcion">
        <form ref={formulario} className="panel seccion" onSubmit={enviar} noValidate aria-labelledby="titulo-abrir">
          <div className="seccion__cabeza">
            <h2 id="titulo-abrir">Abrir una inscripción</h2>
          </div>

          {problema && (
            <Aviso
              tono="error"
              rol="alert"
              titulo={problema.titulo}
              accion={
                problema.enlace && (
                  <BotonEnlace to={problema.enlace.a} icono={UserRound}>
                    {problema.enlace.texto}
                  </BotonEnlace>
                )
              }
            >
              {problema.texto}
            </Aviso>
          )}
          {pedidaSinConsentimiento && pedida.data && (
            <Aviso
              tono="aviso"
              titulo={`${pedida.data.nombre} no tiene consentimiento vigente`}
              accion={
                <BotonEnlace to={`/personas/${pedida.data.id}`} icono={UserRound}>
                  Ir a su ficha
                </BotonEnlace>
              }
            >
              Para inscribirla, primero registra su consentimiento.
            </Aviso>
          )}

          {sinPersonas ? (
            <Aviso
              tono="info"
              titulo="Nadie tiene consentimiento vigente"
              accion={
                <BotonEnlace to="/personas" icono={Users}>
                  Ir a Personas
                </BotonEnlace>
              }
            >
              Solo se inscribe a quien dio su consentimiento. Regístralo en la ficha de la persona.
            </Aviso>
          ) : (
            <Campo etiqueta="Persona" error={errores.persona} ayuda="Solo aparecen las personas con consentimiento vigente.">
              {(control) => (
                <select
                  {...control}
                  className="control"
                  name="persona"
                  disabled={personas.isPending}
                  value={personaId}
                  onChange={(evento) => recordar('persona', evento.target.value)}
                >
                  <option value="">{personas.isPending ? 'Cargando personas…' : 'Elige a la persona…'}</option>
                  {personas.data?.map((persona) => (
                    <option key={persona.id} value={persona.id}>
                      {textoPersona(persona)}
                    </option>
                  ))}
                </select>
              )}
            </Campo>
          )}

          {sinCamaras ? (
            <Aviso
              tono="info"
              titulo="No hay cámaras activas"
              accion={
                <BotonEnlace to="/camaras" icono={Cctv}>
                  Ir a Cámaras
                </BotonEnlace>
              }
            >
              Crea una cámara o activa la que vas a usar.
            </Aviso>
          ) : (
            <Campo etiqueta="Cámara" error={errores.camara} ayuda={ayudaCamara}>
              {(control) => (
                <select
                  {...control}
                  className="control"
                  name="camara"
                  disabled={camaras.isPending}
                  value={camara ? codigo : ''}
                  onChange={(evento) => {
                    recordar('camara', evento.target.value)
                    setOcupada(undefined)
                  }}
                >
                  <option value="">{camaras.isPending ? 'Cargando cámaras…' : 'Elige la cámara…'}</option>
                  {activas.map((opcion) => (
                    <option key={opcion.codigo} value={opcion.codigo}>
                      {textoCamara(opcion)}
                    </option>
                  ))}
                </select>
              )}
            </Campo>
          )}

          {ocupada && (
            <CamaraOcupada
              codigo={ocupada}
              ocupando={abrir.isPending}
              onLibre={() => {
                setOcupada(undefined)
                abrirCon({ persona_id: personaId, dispositivo: ocupada })
              }}
            />
          )}

          {!sinPersonas && !sinCamaras && (
            <div className="botones">
              <Boton type="submit" variante="primario" icono={ScanFace} cargando={abrir.isPending} textoCargando="Abriendo…">
                Abrir inscripción
              </Boton>
            </div>
          )}
        </form>

        {enCurso.length > 0 && (
          <section className="panel seccion" aria-labelledby="titulo-en-curso">
            <div className="seccion__cabeza">
              <h2 id="titulo-en-curso">En curso</h2>
            </div>
            <ul className="en-curso">
              {enCurso.map((camaraEnCurso) => (
                <EnCurso key={camaraEnCurso.codigo} camara={camaraEnCurso} />
              ))}
            </ul>
          </section>
        )}
      </div>
    </>
  )
}

/** Una inscripción en curso: de quién es (su inscripción) y cuánto lleva (la de la cámara, que se refresca sola). */
function EnCurso({ camara }: { camara: Dispositivo }) {
  const corta = camara.inscripcion_activa
  const inscripcion = useInscripcion(corta?.id, { vivo: false })
  const ahora = usarAhora(Boolean(corta))
  if (!corta) return null
  return (
    <li className="en-curso__item">
      <div>
        <p className="en-curso__nombre">
          {camara.nombre} · {inscripcion.data ? inscripcion.data.persona.nombre : 'Cargando…'}
        </p>
        <p className="tabla__secundario numeros">
          Muestra {corta.muestras} de {corta.requeridas} · vence en {formatearRestante(restanteHasta(corta.vence, ahora))}
        </p>
      </div>
      <Link to={`/inscripcion/${corta.id}`}>
        Ver<span className="visualmente-oculto"> la inscripción de la cámara {camara.nombre}</span>
      </Link>
    </li>
  )
}

/**
 * 409 inscripcion_activa: la cámara ya tiene una. Se toma de inscripcion_activa de la cámara (GET de la cámara), se
 * dice de quién es y se ofrece verla o cancelarla para abrir la nueva (RF-03 · C5).
 */
function CamaraOcupada({ codigo, ocupando, onLibre }: { codigo: string; ocupando: boolean; onLibre: () => void }) {
  const camara = useCamara(codigo)
  const corta = camara.data?.inscripcion_activa
  const inscripcion = useInscripcion(corta?.id, { vivo: false })
  const cancelar = useCancelarInscripcion()
  const ahora = usarAhora(Boolean(corta))
  const [confirmar, setConfirmar] = useState(false)
  const [error, setError] = useState<string>()
  const nombreCamara = camara.data?.nombre ?? codigo
  const ocupante = inscripcion.data?.persona.nombre

  if (camara.isPending || (corta && inscripcion.isPending)) {
    return (
      <Aviso tono="aviso" rol="alert" titulo={`La cámara ${nombreCamara} ya tiene una inscripción en curso`}>
        Buscando de quién es…
      </Aviso>
    )
  }

  // Terminó mientras tanto (se completó, venció o la cancelaron): ya se puede abrir la nueva.
  if (!corta) {
    return (
      <Aviso
        tono="info"
        rol="status"
        titulo={`La inscripción que ocupaba ${nombreCamara} ya terminó`}
        accion={
          <Boton variante="secundario" icono={ScanFace} cargando={ocupando} textoCargando="Abriendo…" onClick={onLibre}>
            Abrir la nueva
          </Boton>
        }
      >
        Ya puedes abrir la inscripción.
      </Aviso>
    )
  }

  function confirmarCancelacion() {
    if (!corta) return
    setError(undefined)
    cancelar.mutate(
      { id: corta.id, personaId: inscripcion.data?.persona.id },
      {
        onSuccess: () => {
          setConfirmar(false)
          onLibre()
        },
        onError: (fallo) => {
          // Si ya había terminado, la cámara quedó libre igual.
          if (fallo instanceof ErrorApi && fallo.codigo === 'inscripcion_terminada') {
            setConfirmar(false)
            onLibre()
            return
          }
          setError(detalleDe(fallo))
        },
      },
    )
  }

  return (
    <>
      <Aviso tono="aviso" rol="alert" titulo={`La cámara ${nombreCamara} ya está inscribiendo a ${ocupante ?? 'otra persona'}`}>
        <p className="numeros">
          Muestra {corta.muestras} de {corta.requeridas} · vence en {formatearRestante(restanteHasta(corta.vence, ahora))}
        </p>
        <div className="botones aviso__acciones">
          <BotonEnlace to={`/inscripcion/${corta.id}`}>
            Ver su avance
          </BotonEnlace>
          <Boton variante="peligro-suave" onClick={() => setConfirmar(true)}>
            Cancelarla y abrir la nueva
          </Boton>
        </div>
      </Aviso>
      <DialogoConfirmacion
        abierto={confirmar}
        titulo={`¿Cancelar la inscripción de ${ocupante ?? 'la otra persona'}?`}
        textoConfirmar="Cancelar y abrir la nueva"
        textoCargando="Cancelando…"
        textoCancelar="No cancelar"
        ocupado={cancelar.isPending || ocupando}
        error={error}
        onConfirmar={confirmarCancelacion}
        onCerrar={() => setConfirmar(false)}
      >
        <p>
          Las muestras que ya se aceptaron se conservan. Después se abre la nueva inscripción en la cámara {nombreCamara}.
        </p>
      </DialogoConfirmacion>
    </>
  )
}
