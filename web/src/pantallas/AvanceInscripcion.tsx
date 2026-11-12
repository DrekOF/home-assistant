/**
 * Nombre: AvanceInscripcion.tsx
 * Descripción: Avance en vivo de una inscripción («Muestra 3 de 5»), el tiempo que falta, el motivo del último rechazo, cancelar y cómo terminó (RF-03 · C4 a C6, R7, R9).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { ArrowLeft, RotateCw, ScanFace, SearchX, UserRound, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { detalleDe, ErrorApi, type EstadoInscripcion, type Inscripcion, type MotivoMuestra } from '../api/cliente'
import { useCamara, useCancelarInscripcion, useInscripcion } from '../api/consultas'
import { usarAhora } from '../componentes/ahora'
import { Aviso } from '../componentes/Aviso'
import { BarraAvance } from '../componentes/BarraAvance'
import { Boton, BotonEnlace } from '../componentes/Boton'
import { DialogoConfirmacion } from '../componentes/DialogoConfirmacion'
import { Esqueleto } from '../componentes/Esqueleto'
import { InsigniaEstado, type Tono } from '../componentes/InsigniaEstado'
import { usarTitulo } from '../componentes/titulo'
import { Vacio } from '../componentes/Vacio'
import { formatearFechaHora } from '../logica/fechas'
import {
  contarMuestras,
  formatearRestante,
  MOTIVOS,
  NOMBRES_ESTADO,
  restanteHasta,
  textoConservadas,
} from '../logica/inscripcion'

const TONOS: Record<EstadoInscripcion, Tono> = { activa: 'aviso', completada: 'ok', vencida: 'aviso', cancelada: 'neutro' }

export function AvanceInscripcion() {
  const { inscripcionId = '' } = useParams()
  const consulta = useInscripcion(inscripcionId)
  usarTitulo(consulta.data ? `Inscripción de ${consulta.data.persona.nombre}` : 'Inscripción')

  if (consulta.isPending) {
    return (
      <div aria-busy="true">
        <p className="visualmente-oculto" role="status">
          Cargando la inscripción…
        </p>
        <Esqueleto ancho="22rem" alto="2rem" />
      </div>
    )
  }
  if (!consulta.data) {
    const noExiste = consulta.error instanceof ErrorApi && consulta.error.estado === 404
    return noExiste ? (
      <div className="panel">
        <Vacio
          icono={SearchX}
          titulo="Esa inscripción no existe"
          acciones={
            <BotonEnlace to="/inscripcion" icono={ScanFace}>
              Abrir una inscripción
            </BotonEnlace>
          }
        >
          La dirección está incompleta o la inscripción ya no existe. Las que siguen en curso están en Inscripción y en
          Cámaras.
        </Vacio>
      </div>
    ) : (
      <Aviso
        tono="error"
        rol="alert"
        titulo="No se pudo cargar la inscripción"
        accion={
          <Boton icono={RotateCw} onClick={() => void consulta.refetch()}>
            Reintentar
          </Boton>
        }
      >
        {detalleDe(consulta.error)}
      </Aviso>
    )
  }
  return <Avance key={consulta.data.id} inscripcion={consulta.data} sinConexion={consulta.isError} />
}

/**
 * El motivo no se borra al aceptar otra muestra (R7): si se aceptó una después de este rechazo, se dice y el
 * motivo pasa a gris. Guarda cuántas muestras había cuando apareció el motivo.
 */
function usarMotivo(inscripcion: Inscripcion): { motivo: MotivoMuestra | null; despues: boolean } {
  const [registro, setRegistro] = useState({ motivo: inscripcion.ultimo_motivo, muestras: inscripcion.muestras })
  if (registro.motivo !== inscripcion.ultimo_motivo) {
    setRegistro({ motivo: inscripcion.ultimo_motivo, muestras: inscripcion.muestras })
  }
  const despues =
    inscripcion.ultimo_motivo !== null &&
    registro.motivo === inscripcion.ultimo_motivo &&
    inscripcion.muestras > registro.muestras
  return { motivo: inscripcion.ultimo_motivo, despues }
}

function Avance({ inscripcion, sinConexion }: { inscripcion: Inscripcion; sinConexion: boolean }) {
  const camara = useCamara(inscripcion.dispositivo)
  const nombreCamara = camara.data?.nombre ?? inscripcion.dispositivo
  const activa = inscripcion.estado === 'activa'
  const ahora = usarAhora(activa)
  const { motivo, despues } = usarMotivo(inscripcion)
  const cancelar = useCancelarInscripcion()
  const [confirmar, setConfirmar] = useState(false)
  const [error, setError] = useState<string>()
  const persona = inscripcion.persona
  const otra = `/inscripcion?persona=${persona.id}&camara=${inscripcion.dispositivo}`

  function confirmarCancelacion() {
    setError(undefined)
    cancelar.mutate(
      { id: inscripcion.id, personaId: persona.id },
      {
        onSuccess: () => setConfirmar(false),
        onError: (fallo) => {
          // Ya había terminado: la consulta se renueva sola y muestra cómo terminó.
          if (fallo instanceof ErrorApi && fallo.codigo === 'inscripcion_terminada') setConfirmar(false)
          else setError(detalleDe(fallo))
        },
      },
    )
  }

  return (
    <>
      <Link className="miga" to="/inscripcion">
        <ArrowLeft aria-hidden />
        Inscripción
      </Link>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>Inscripción de {persona.nombre}</h1>
          <p className="encabezado__resumen botones">
            <InsigniaEstado tono={TONOS[inscripcion.estado]} icono={activa ? ScanFace : undefined}>
              {NOMBRES_ESTADO[inscripcion.estado]}
            </InsigniaEstado>
            <span>
              Cámara {nombreCamara} · abierta el {formatearFechaHora(inscripcion.creada)}
            </span>
          </p>
        </div>
      </div>

      {/* La región de estado existe siempre: así se anuncia cómo terminó. Mide lo mismo que el panel. */}
      <div className="estado-accion avance-inscripcion__estado" role="status">
        {inscripcion.estado === 'completada' && (
          <Aviso tono="ok" titulo="Inscripción completada">
            <p>
              Se guardaron {contarMuestras(inscripcion.muestras)} de {persona.nombre}. La cámara {nombreCamara} vuelve a
              reconocer.
            </p>
            {/* Las acciones van debajo del texto: a su lado lo apretarían en el ancho del panel. */}
            <div className="botones aviso__acciones">
              <BotonEnlace to={`/personas/${persona.id}`} icono={UserRound}>
                Ver la ficha
              </BotonEnlace>
              <BotonEnlace to={`/inscripcion?camara=${inscripcion.dispositivo}`} icono={ScanFace}>
                Inscribir a otra persona
              </BotonEnlace>
            </div>
          </Aviso>
        )}
        {inscripcion.estado === 'vencida' && (
          <Aviso tono="aviso" titulo="La inscripción venció">
            <p>
              Llegó a {inscripcion.muestras} de {inscripcion.requeridas} muestras.{' '}
              {textoConservadas(inscripcion.muestras)} La cámara {nombreCamara} vuelve a reconocer.
            </p>
            <div className="botones aviso__acciones">
              <BotonEnlace to={otra} icono={ScanFace}>
                Abrir otra inscripción
              </BotonEnlace>
            </div>
          </Aviso>
        )}
        {inscripcion.estado === 'cancelada' && (
          <Aviso tono="info" titulo="Inscripción cancelada">
            <p>
              {textoConservadas(inscripcion.muestras)} La cámara {nombreCamara} vuelve a reconocer.
            </p>
            <div className="botones aviso__acciones">
              <BotonEnlace to={otra} icono={ScanFace}>
                Abrir otra inscripción
              </BotonEnlace>
            </div>
          </Aviso>
        )}
      </div>

      {activa && sinConexion && (
        <Aviso tono="aviso" titulo="Sin conexión con el servidor">
          Se sigue intentando cada segundo. El avance se ve cuando vuelva la conexión.
        </Aviso>
      )}

      <section className="panel seccion avance-inscripcion" aria-labelledby="titulo-avance">
        <h2 id="titulo-avance" className="visualmente-oculto">
          Avance
        </h2>
        <BarraAvance
          actual={inscripcion.muestras}
          total={inscripcion.requeridas}
          detalle={
            activa ? (
              <>
                Vence en <span className="numeros">{formatearRestante(restanteHasta(inscripcion.vence, ahora))}</span>
              </>
            ) : undefined
          }
        />

        {/* Siempre montada: un lector de pantalla oye el motivo cuando cambia, no el tiempo de cada segundo. */}
        <p className="visualmente-oculto" aria-live="polite">
          {motivo ? `Último rechazo: ${MOTIVOS[motivo].que} ${MOTIVOS[motivo].hacer}` : ''}
        </p>
        {/* Completada, el último rechazo ya no importa; vencida o cancelada, ayuda a entender por qué. */}
        {motivo && inscripcion.estado !== 'completada' && (
          // La clave hace que el aviso entre de nuevo cuando cambia el motivo.
          <div key={motivo} className="motivo">
            <Aviso tono={despues || !activa ? 'info' : 'aviso'} titulo={`Último rechazo: ${MOTIVOS[motivo].que}`}>
              <p>{MOTIVOS[motivo].hacer}</p>
              {despues && activa && <p className="motivo__nota">Después se aceptó otra muestra.</p>}
            </Aviso>
          </div>
        )}

        {activa && (
          <>
            {camara.data && !camara.data.en_linea && (
              <Aviso tono="aviso">La cámara {nombreCamara} está sin conexión: no llegarán muestras hasta que se conecte.</Aviso>
            )}
            <div className="avance-inscripcion__pie">
              <p className="texto-secundario">
                Que la persona mire de frente a la cámara {nombreCamara}: cada cara válida suma una muestra. Esta página se
                actualiza sola.
              </p>
              <Boton variante="peligro-suave" icono={X} onClick={() => setConfirmar(true)}>
                Cancelar inscripción
              </Boton>
            </div>
          </>
        )}
      </section>

      <DialogoConfirmacion
        abierto={confirmar}
        titulo={`¿Cancelar la inscripción de ${persona.nombre}?`}
        textoConfirmar="Cancelar inscripción"
        textoCargando="Cancelando…"
        textoCancelar="Seguir inscribiendo"
        ocupado={cancelar.isPending}
        error={error}
        onConfirmar={confirmarCancelacion}
        onCerrar={() => setConfirmar(false)}
      >
        <p>
          {textoConservadas(inscripcion.muestras)} La cámara {nombreCamara} vuelve a reconocer.
        </p>
      </DialogoConfirmacion>
    </>
  )
}
