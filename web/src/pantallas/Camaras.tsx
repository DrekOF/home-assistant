/**
 * Nombre: Camaras.tsx
 * Descripción: Lista de cámaras con su estado, si están en línea, su último contacto y su modo, con la inscripción en curso; se refresca sola (RF-09 · C2, RF-10 · C3).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { Cctv, Plus, RotateCw, ScanFace, Wifi, WifiOff } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import { detalleDe, type Dispositivo } from '../api/cliente'
import { useCamaras } from '../api/consultas'
import { usarAhora } from '../componentes/ahora'
import { Aviso } from '../componentes/Aviso'
import { Boton, BotonEnlace } from '../componentes/Boton'
import { FilasEsqueleto } from '../componentes/Esqueleto'
import { InsigniaEstado } from '../componentes/InsigniaEstado'
import { usarTitulo } from '../componentes/titulo'
import { Vacio } from '../componentes/Vacio'
import { NOMBRES_TIPO } from '../logica/camaras'
import { formatearFechaHora } from '../logica/fechas'
import { formatearRestante, restanteHasta } from '../logica/inscripcion'

const COLUMNAS = 4

export function Camaras() {
  usarTitulo('Cámaras')
  const consulta = useCamaras()
  const { state } = useLocation() as { state: { creada?: string } | null }
  const camaras = consulta.data
  // El tiempo que falta de cada inscripción avanza cada segundo, aunque la lista se pida cada 5.
  const ahora = usarAhora(Boolean(camaras?.some((camara) => camara.inscripcion_activa)))

  return (
    <>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>Cámaras</h1>
          <p className="encabezado__resumen numeros">
            {camaras
              ? `${camaras.length === 1 ? '1 cámara registrada' : `${camaras.length} cámaras registradas`}. La lista se actualiza sola.`
              : 'Cargando…'}
          </p>
        </div>
        <BotonEnlace to="/camaras/nueva" variante="primario" icono={Plus}>
          Nueva cámara
        </BotonEnlace>
      </div>

      <div className="estado-accion" role="status">
        {state?.creada && <Aviso tono="ok">Cámara {state.creada} creada.</Aviso>}
      </div>

      <section className="panel" aria-labelledby="titulo-camaras">
        <h2 id="titulo-camaras" className="visualmente-oculto">
          Lista de cámaras
        </h2>
        {consulta.isError && !camaras ? (
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
        ) : camaras && camaras.length === 0 ? (
          <Vacio
            icono={Cctv}
            titulo="Todavía no hay cámaras"
            acciones={
              <BotonEnlace to="/camaras/nueva" variante="primario" icono={Plus}>
                Nueva cámara
              </BotonEnlace>
            }
          >
            Registra la primera: el simulador, una placa o una cámara de respaldo. Su token se muestra una sola vez, al crearla.
          </Vacio>
        ) : (
          <div className="panel--tabla">
            <table className="tabla" aria-busy={consulta.isPending || undefined}>
              <thead>
                <tr>
                  <th scope="col">Cámara</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Conexión</th>
                  <th scope="col">Modo</th>
                </tr>
              </thead>
              <tbody>
                {!camaras ? (
                  <FilasEsqueleto filas={3} columnas={COLUMNAS} />
                ) : (
                  camaras.map((camara) => <FilaCamara key={camara.codigo} camara={camara} ahora={ahora} />)
                )}
              </tbody>
            </table>
          </div>
        )}
        {consulta.isError && camaras && (
          <div className="seccion">
            <Aviso tono="aviso">No se pudo actualizar la lista: se ve la última que llegó. Se vuelve a intentar sola.</Aviso>
          </div>
        )}
      </section>
    </>
  )
}

function FilaCamara({ camara, ahora }: { camara: Dispositivo; ahora: number }) {
  const inscripcion = camara.inscripcion_activa
  return (
    <tr>
      <td className="tabla__nombre">
        <Link to={`/camaras/${camara.codigo}`}>{camara.nombre}</Link>
        <div className="tabla__secundario">
          <span className="mono" translate="no">
            {camara.codigo}
          </span>
          {' · '}
          {NOMBRES_TIPO[camara.tipo]}
        </div>
      </td>
      <td>
        {camara.activo ? (
          <InsigniaEstado tono="ok">Activa</InsigniaEstado>
        ) : (
          <InsigniaEstado tono="neutro">Inactiva</InsigniaEstado>
        )}
      </td>
      <td>
        {camara.en_linea ? (
          <InsigniaEstado tono="ok" icono={Wifi}>
            En línea
          </InsigniaEstado>
        ) : (
          <InsigniaEstado tono="neutro" icono={WifiOff}>
            Sin conexión
          </InsigniaEstado>
        )}
        <div className="tabla__secundario">
          {camara.ultimo_contacto ? `Último contacto: ${formatearFechaHora(camara.ultimo_contacto)}` : 'Sin contacto todavía'}
        </div>
      </td>
      <td>
        {inscripcion ? (
          <>
            {/* Mientras inscribe, la cámara no reconoce ni abre la puerta (R9): por eso va en ámbar. */}
            <InsigniaEstado tono="aviso" icono={ScanFace}>
              Inscribiendo
            </InsigniaEstado>
            <div className="tabla__secundario numeros">
              {inscripcion.muestras} de {inscripcion.requeridas} · vence en{' '}
              {formatearRestante(restanteHasta(inscripcion.vence, ahora))}
            </div>
            <Link className="tabla__enlace" to={`/inscripcion/${inscripcion.id}`}>
              Ver la inscripción
            </Link>
          </>
        ) : (
          <span className="tabla__secundario">Reconoce</span>
        )}
      </td>
    </tr>
  )
}
