/**
 * Nombre: SeccionConsentimiento.tsx
 * Descripción: Consentimiento en la ficha: texto y aviso de que es opcional, registro en web o papel, revocación confirmada e historial (RF-02 · C2, C3 y C5).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { UseQueryResult } from '@tanstack/react-query'
import { CircleExclamationPoint, RotateCw, ShieldCheck, ShieldOff } from 'lucide-react'
import { Fragment, useId, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { detalleDe, type Consentimiento, type Persona } from '../api/cliente'
import {
  useConsentimientos,
  useRegistrarConsentimiento,
  useRevocarConsentimiento,
  useTextoConsentimiento,
} from '../api/consultas'
import { Aviso } from '../componentes/Aviso'
import { Boton } from '../componentes/Boton'
import { Campo, enfocarPrimerError } from '../componentes/Campo'
import { DialogoConfirmacion } from '../componentes/DialogoConfirmacion'
import { Esqueleto } from '../componentes/Esqueleto'
import { InsigniaEstado } from '../componentes/InsigniaEstado'
import { aIsoColombia, formatearFechaHora, valorLocalColombia } from '../logica/fechas'
import { leerParrafos } from '../logica/texto'
import { hayErrores, validarConsentimiento, type Errores, type MedioConsentimiento } from '../logica/validaciones'
import { NOMBRES_MEDIO } from './textos'

type Props = { persona: Persona; consentimiento: UseQueryResult<Consentimiento | null> }

export function SeccionConsentimiento({ persona, consentimiento }: Props) {
  const revocar = useRevocarConsentimiento(persona.id)
  const [confirmando, setConfirmando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const titulo = useRef<HTMLHeadingElement>(null)

  /** Tras registrar o revocar, el formulario desaparece: el foco vuelve al título de la sección. */
  function terminar(mensaje: string) {
    setAviso(mensaje)
    requestAnimationFrame(() => titulo.current?.focus())
  }

  const vigente = consentimiento.data

  return (
    <section className="panel seccion" aria-labelledby="titulo-consentimiento">
      <div className="seccion__cabeza">
        <h2 id="titulo-consentimiento" ref={titulo} tabIndex={-1}>
          Consentimiento
        </h2>
        {consentimiento.isSuccess &&
          (vigente ? (
            <InsigniaEstado tono="ok">Vigente</InsigniaEstado>
          ) : (
            <InsigniaEstado tono="neutro">Sin consentimiento</InsigniaEstado>
          ))}
      </div>

      <div role="status">{aviso && <Aviso tono="ok">{aviso}</Aviso>}</div>

      {consentimiento.isPending ? (
        <div aria-hidden className="vigente">
          <Esqueleto ancho="90%" />
          <Esqueleto ancho="60%" />
        </div>
      ) : consentimiento.isError ? (
        <Aviso
          tono="error"
          rol="alert"
          titulo="No se pudo cargar el consentimiento"
          accion={
            <Boton icono={RotateCw} onClick={() => void consentimiento.refetch()}>
              Reintentar
            </Boton>
          }
        >
          {detalleDe(consentimiento.error)}
        </Aviso>
      ) : vigente ? (
        <div className="vigente">
          <dl className="datos">
            <dt>Versión del texto</dt>
            <dd>{vigente.version_texto}</dd>
            <dt>Medio</dt>
            <dd>{NOMBRES_MEDIO[vigente.medio]}</dd>
            <dt>{vigente.medio === 'papel' ? 'Firmado' : 'Aceptado'}</dt>
            <dd>{formatearFechaHora(vigente.aceptado_en)}</dd>
            {vigente.registrado_por && (
              <>
                <dt>Lo registró</dt>
                <dd>{vigente.registrado_por}</dd>
              </>
            )}
          </dl>
          <p className="tabla__secundario">
            La persona puede revocarlo cuando quiera. Al revocarlo se borran sus huellas y se cancela su inscripción
            activa, si la tiene.
          </p>
          <div className="botones">
            <Boton variante="peligro-suave" icono={ShieldOff} onClick={() => setConfirmando(true)}>
              Revocar consentimiento
            </Boton>
          </div>
        </div>
      ) : (
        <RegistrarConsentimiento
          persona={persona}
          onRegistrado={() => terminar('Consentimiento registrado. Ya puedes inscribir a esta persona.')}
        />
      )}

      <Historial personaId={persona.id} />

      <DialogoConfirmacion
        abierto={confirmando}
        titulo={`¿Revocar el consentimiento de ${persona.nombre}?`}
        textoConfirmar="Revocar y borrar huellas"
        textoCargando="Revocando…"
        ocupado={revocar.isPending}
        error={revocar.isError ? detalleDe(revocar.error) : undefined}
        onCerrar={() => {
          setConfirmando(false)
          revocar.reset()
        }}
        onConfirmar={() =>
          revocar.mutate(undefined, {
            onSuccess: () => {
              setConfirmando(false)
              terminar('Consentimiento revocado: se borraron sus huellas y se canceló su inscripción activa, si la tenía.')
            },
          })
        }
      >
        <p>
          <strong>
            Se borran sus huellas
            {persona.muestras > 0 && ` (${persona.muestras} ${persona.muestras === 1 ? 'muestra' : 'muestras'})`} y se
            cancela su inscripción activa, si la tiene.
          </strong>{' '}
          La cámara deja de reconocerla.
        </p>
        <p>No se puede deshacer: para volver a inscribirla hay que registrar un consentimiento nuevo.</p>
      </DialogoConfirmacion>
    </section>
  )
}

function RegistrarConsentimiento({ persona, onRegistrado }: { persona: Persona; onRegistrado: () => void }) {
  const texto = useTextoConsentimiento()
  const registrar = useRegistrarConsentimiento(persona.id)
  const [medio, setMedio] = useState<MedioConsentimiento>('web')
  const [aceptadoEn, setAceptadoEn] = useState('')
  const [acepta, setAcepta] = useState(false)
  const [errores, setErrores] = useState<Errores<'acepta' | 'aceptadoEn'>>({})
  const formulario = useRef<HTMLFormElement>(null)
  const idErrorAcepta = useId()

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const encontrados = validarConsentimiento({ medio, acepta, aceptadoEn })
    setErrores(encontrados)
    if (hayErrores(encontrados)) {
      enfocarPrimerError(formulario.current)
      return
    }
    if (!texto.data) return
    const firma = medio === 'papel' ? aIsoColombia(aceptadoEn) : null
    registrar.mutate(
      { version_texto: texto.data.version, acepta: true, medio, ...(firma ? { aceptado_en: firma } : {}) },
      { onSuccess: onRegistrado },
    )
  }

  return (
    <>
      <Aviso tono="info" titulo="El consentimiento es opcional">
        Sin consentimiento, AccesIA no guarda la huella de esta persona ni la reconoce en la puerta. Su asistencia se
        registra a mano en <Link to="/asistencia">Asistencia</Link>.
      </Aviso>

      {texto.isPending ? (
        <div className="texto-legal" aria-hidden>
          <Esqueleto ancho="70%" />
          <Esqueleto ancho="95%" />
          <Esqueleto ancho="85%" />
        </div>
      ) : texto.isError ? (
        <Aviso
          tono="error"
          rol="alert"
          titulo="No se pudo cargar el texto del consentimiento"
          accion={
            <Boton icono={RotateCw} onClick={() => void texto.refetch()}>
              Reintentar
            </Boton>
          }
        >
          {detalleDe(texto.error)}
        </Aviso>
      ) : (
        <div
          className="texto-legal"
          role="region"
          tabIndex={0}
          aria-label={`Texto de la autorización, versión ${texto.data.version}`}
        >
          <p className="texto-legal__titulo">Texto que lee la persona · versión {texto.data.version}</p>
          {leerParrafos(texto.data.texto).map((parrafo, indice) => (
            <p key={indice}>
              {parrafo.map((fragmento, parte) =>
                fragmento.negrita ? (
                  <strong key={parte}>{fragmento.texto}</strong>
                ) : (
                  <Fragment key={parte}>{fragmento.texto}</Fragment>
                ),
              )}
            </p>
          ))}
        </div>
      )}

      <form ref={formulario} className="consentimiento-form" onSubmit={enviar} noValidate>
        <fieldset>
          <legend>¿Cómo da su consentimiento?</legend>
          <div className="medios">
            <label className="opcion">
              <input type="radio" name="medio" value="web" checked={medio === 'web'} onChange={() => setMedio('web')} />
              <span className="opcion__texto">
                <span>En esta pantalla</span>
                <span className="opcion__detalle">Lee el texto aquí y acepta.</span>
              </span>
            </label>
            <label className="opcion">
              <input
                type="radio"
                name="medio"
                value="papel"
                checked={medio === 'papel'}
                onChange={() => setMedio('papel')}
              />
              <span className="opcion__texto">
                <span>En papel</span>
                <span className="opcion__detalle">Firmó el formato impreso.</span>
              </span>
            </label>
          </div>
        </fieldset>

        {medio === 'papel' && (
          <Campo
            etiqueta="Fecha y hora de la firma"
            error={errores.aceptadoEn}
            ayuda="En hora de Colombia. No puede ser futura."
          >
            {(control) => (
              <input
                {...control}
                className="control"
                type="datetime-local"
                name="aceptado_en"
                autoComplete="off"
                max={valorLocalColombia()}
                value={aceptadoEn}
                onChange={(evento) => setAceptadoEn(evento.target.value)}
              />
            )}
          </Campo>
        )}

        <div className="campo">
          <label className="opcion" aria-invalid={errores.acepta ? true : undefined}>
            <input
              type="checkbox"
              name="acepta"
              checked={acepta}
              aria-invalid={errores.acepta ? true : undefined}
              aria-describedby={errores.acepta ? idErrorAcepta : undefined}
              onChange={(evento) => setAcepta(evento.target.checked)}
            />
            <span className="opcion__texto">
              <span>
                {persona.nombre} leyó la versión {texto.data?.version ?? 'vigente'} del texto y acepta el tratamiento de sus
                datos biométricos.
              </span>
            </span>
          </label>
          {errores.acepta && (
            <p className="campo__error" id={idErrorAcepta}>
              <CircleExclamationPoint aria-hidden />
              {errores.acepta}
            </p>
          )}
        </div>

        {registrar.isError && (
          <Aviso tono="error" rol="alert" titulo="No se pudo registrar">
            {detalleDe(registrar.error)}
          </Aviso>
        )}

        <div className="botones">
          <Boton
            type="submit"
            variante="primario"
            icono={ShieldCheck}
            cargando={registrar.isPending}
            textoCargando="Registrando…"
            disabled={!texto.data}
          >
            Registrar consentimiento
          </Boton>
        </div>
      </form>
    </>
  )
}

function Historial({ personaId }: { personaId: string }) {
  const historial = useConsentimientos(personaId)
  return (
    <div className="historial">
      <h3>Historial</h3>
      {historial.isPending ? (
        <Esqueleto ancho="60%" />
      ) : historial.isError ? (
        <p className="tabla__secundario">No se pudo cargar el historial: {detalleDe(historial.error)}</p>
      ) : historial.data.length === 0 ? (
        <p className="tabla__secundario">Todavía no hay consentimientos registrados.</p>
      ) : (
        <ol className="historial__lista">
          {historial.data.map((item) => (
            <li key={item.id} className="historial__item">
              <p>
                <strong>Versión {item.version_texto}</strong> · {NOMBRES_MEDIO[item.medio]}
              </p>
              <p className="tabla__secundario">
                Aceptado el {formatearFechaHora(item.aceptado_en)}
                {item.registrado_por && ` · lo registró ${item.registrado_por}`}
              </p>
              {item.revocado_en && (
                <p className="tabla__secundario">Revocado el {formatearFechaHora(item.revocado_en)}</p>
              )}
              <div className="historial__estado">
                {item.revocado_en ? (
                  <InsigniaEstado tono="neutro">Revocado</InsigniaEstado>
                ) : (
                  <InsigniaEstado tono="ok">Vigente</InsigniaEstado>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
