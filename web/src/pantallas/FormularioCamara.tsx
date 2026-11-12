/**
 * Nombre: FormularioCamara.tsx
 * Descripción: Crear una cámara y ver su token una sola vez, y la ficha de una cámara: editarla, activarla o desactivarla y cambiar su token (RF-10 · C1 a C3).
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { ArrowLeft, Cctv, KeyRound, Plus, RotateCw, Save, ScanFace, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useBlocker, useNavigate, useParams } from 'react-router'
import { detalleDe, ErrorApi, type Dispositivo, type DispositivoCambios, type TipoCamara } from '../api/cliente'
import {
  pedirCamaraNueva,
  pedirTokenNuevo,
  useCamara,
  useEditarCamara,
  usePeticionConToken,
  type CamaraConToken,
} from '../api/consultas'
import { usarAhora } from '../componentes/ahora'
import { Aviso } from '../componentes/Aviso'
import { Boton, BotonEnlace } from '../componentes/Boton'
import { Campo, enfocarPrimerError } from '../componentes/Campo'
import { DialogoConfirmacion } from '../componentes/DialogoConfirmacion'
import { DialogoToken } from '../componentes/DialogoToken'
import { Esqueleto } from '../componentes/Esqueleto'
import { InsigniaEstado } from '../componentes/InsigniaEstado'
import { usarTitulo } from '../componentes/titulo'
import { Vacio } from '../componentes/Vacio'
import { AYUDAS_TIPO, campoDe422, NOMBRES_TIPO, TIPOS_CAMARA } from '../logica/camaras'
import { formatearFechaHora } from '../logica/fechas'
import { formatearRestante, restanteHasta } from '../logica/inscripcion'
import {
  hayErrores,
  limpiarNombre,
  NOMBRE_CAMARA_MAX,
  validarCamara,
  type CampoCamara,
  type Errores,
} from '../logica/validaciones'

export function FormularioCamara() {
  const { codigo } = useParams()
  const camara = useCamara(codigo)
  usarTitulo(codigo ? (camara.data?.nombre ?? 'Cámara') : 'Nueva cámara')

  if (!codigo) return <NuevaCamara />
  if (camara.isPending) {
    return (
      <div aria-busy="true">
        <p className="visualmente-oculto" role="status">
          Cargando la cámara…
        </p>
        <Esqueleto ancho="16rem" alto="2rem" />
      </div>
    )
  }
  if (camara.isError) return <CamaraNoDisponible error={camara.error} reintentar={() => void camara.refetch()} />
  return <FichaCamara key={codigo} camara={camara.data} />
}

type Valores = { codigo: string; nombre: string; tipo: TipoCamara; url: string; activo: boolean }

function valoresDe(camara?: Dispositivo): Valores {
  return {
    codigo: camara?.codigo ?? '',
    nombre: camara?.nombre ?? '',
    tipo: camara?.tipo ?? 'simulador',
    url: camara?.url_captura ?? '',
    activo: camara?.activo ?? true,
  }
}

/** Dónde va un error de la API: junto al campo que nombra (409 codigo_duplicado, 422) o arriba del formulario. */
function ubicarError(error: unknown, conCodigo: boolean): { campo?: CampoCamara; mensaje: string } {
  if (error instanceof ErrorApi && error.codigo === 'codigo_duplicado' && conCodigo) {
    return { campo: 'codigo', mensaje: error.message }
  }
  if (error instanceof ErrorApi && error.codigo === 'validacion') {
    const campo = campoDe422(error.message)
    if (campo && (campo !== 'codigo' || conCodigo)) return { campo, mensaje: error.message }
  }
  return { mensaje: detalleDe(error) }
}

/** Antes de salir con cambios sin guardar, se pregunta (dentro de la web y al cerrar la pestaña). */
function usarSalidaProtegida(sucio: boolean, guardado: { current: boolean }) {
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
  return (
    <DialogoConfirmacion
      abierto={bloqueo.state === 'blocked'}
      titulo="¿Salir sin guardar?"
      textoConfirmar="Salir sin guardar"
      textoCargando="Saliendo…"
      textoCancelar="Seguir editando"
      onConfirmar={() => bloqueo.proceed?.()}
      onCerrar={() => bloqueo.reset?.()}
    >
      <p>Los cambios de esta cámara se pierden.</p>
    </DialogoConfirmacion>
  )
}

type PropsCampos = {
  valores: Valores
  errores: Errores<CampoCamara>
  cambiar: <Clave extends keyof Valores>(clave: Clave, valor: Valores[Clave]) => void
  conCodigo: boolean
}

function CamposCamara({ valores, errores, cambiar, conCodigo }: PropsCampos) {
  const respaldo = valores.tipo === 'respaldo'
  // En la ficha, el formulario comparte el ancho con el estado y el token: va en una columna.
  const ancho = conCodigo ? undefined : 'campo--ancho'
  return (
    <div className="panel formulario__rejilla">
      {conCodigo && (
        <Campo
          etiqueta="Código"
          error={errores.codigo}
          ayuda="De 3 a 32 letras minúsculas, números o guiones. Va en los temas MQTT y no se cambia después."
        >
          {(control) => (
            <input
              {...control}
              className="control mono"
              name="codigo"
              autoComplete="off"
              autoCapitalize="none"
              spellCheck={false}
              maxLength={32}
              placeholder="entrada…"
              value={valores.codigo}
              onChange={(evento) => cambiar('codigo', evento.target.value)}
            />
          )}
        </Campo>
      )}
      <Campo etiqueta="Nombre" error={errores.nombre} className={ancho}>
        {(control) => (
          <input
            {...control}
            className="control"
            name="nombre"
            autoComplete="off"
            maxLength={NOMBRE_CAMARA_MAX}
            placeholder="Entrada principal…"
            value={valores.nombre}
            onChange={(evento) => cambiar('nombre', evento.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Tipo" ayuda={AYUDAS_TIPO[valores.tipo]} className={ancho}>
        {(control) => (
          <select
            {...control}
            className="control"
            name="tipo"
            value={valores.tipo}
            onChange={(evento) => cambiar('tipo', evento.target.value as TipoCamara)}
          >
            {TIPOS_CAMARA.map((tipo) => (
              <option key={tipo} value={tipo}>
                {NOMBRES_TIPO[tipo]}
              </option>
            ))}
          </select>
        )}
      </Campo>
      <Campo
        etiqueta="URL de captura"
        opcional={!respaldo}
        error={errores.url}
        className={ancho}
        ayuda={
          respaldo
            ? 'Obligatoria: el servidor le pide una imagen cada segundo a esta dirección.'
            : 'Solo la usa una cámara de respaldo.'
        }
      >
        {(control) => (
          <input
            {...control}
            className="control mono"
            type="url"
            name="url_captura"
            autoComplete="off"
            spellCheck={false}
            placeholder="http://192.168.137.50/capture…"
            value={valores.url}
            onChange={(evento) => cambiar('url', evento.target.value)}
          />
        )}
      </Campo>
      {/* Al crearla siempre queda activa (DispositivoNuevo no tiene «activo»); se desactiva al editarla. */}
      {!conCodigo && (
        <label className="opcion campo--ancho">
          <input
            type="checkbox"
            name="activo"
            checked={valores.activo}
            onChange={(evento) => cambiar('activo', evento.target.checked)}
          />
          <span className="opcion__texto">
            <span>Cámara activa</span>
            <span className="opcion__detalle">
              Una cámara desactivada no puede enviar recortes ni abrir una inscripción.
            </span>
          </span>
        </label>
      )}
    </div>
  )
}

function NuevaCamara() {
  const inicial = valoresDe()
  const [valores, setValores] = useState(inicial)
  const [errores, setErrores] = useState<Errores<CampoCamara>>({})
  const [errorGeneral, setErrorGeneral] = useState<string>()
  // El token vive solo aquí, mientras el diálogo está abierto (RF-10 · C1).
  const [creada, setCreada] = useState<CamaraConToken | null>(null)
  const peticion = usePeticionConToken()
  const navegar = useNavigate()
  const formulario = useRef<HTMLFormElement>(null)
  const guardado = useRef(false)
  const sucio = JSON.stringify(valores) !== JSON.stringify(inicial)
  const dialogoSalida = usarSalidaProtegida(sucio, guardado)

  function cambiar<Clave extends keyof Valores>(clave: Clave, valor: Valores[Clave]) {
    setValores((actuales) => ({ ...actuales, [clave]: valor }))
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const encontrados = validarCamara(valores)
    setErrores(encontrados)
    setErrorGeneral(undefined)
    if (hayErrores(encontrados)) {
      enfocarPrimerError(formulario.current)
      return
    }
    try {
      const resultado = await peticion.ejecutar(
        pedirCamaraNueva({
          codigo: valores.codigo.trim(),
          nombre: limpiarNombre(valores.nombre),
          tipo: valores.tipo,
          url_captura: valores.url.trim() || null,
        }),
      )
      guardado.current = true
      setCreada(resultado)
    } catch (fallo) {
      const { campo, mensaje } = ubicarError(fallo, true)
      if (campo) {
        setErrores({ [campo]: mensaje })
        enfocarPrimerError(formulario.current)
      } else {
        setErrorGeneral(mensaje)
      }
    }
  }

  function cerrarToken() {
    const nombre = creada?.camara.nombre
    setCreada(null)
    navegar('/camaras', { state: { creada: nombre } })
  }

  return (
    <>
      <Link className="miga" to="/camaras">
        <ArrowLeft aria-hidden />
        Cámaras
      </Link>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>Nueva cámara</h1>
          <p className="encabezado__resumen">Al crearla, su token se muestra una sola vez.</p>
        </div>
      </div>

      <form ref={formulario} className="formulario" onSubmit={(evento) => void enviar(evento)} noValidate>
        {errorGeneral && (
          <Aviso tono="error" rol="alert" titulo="No se pudo crear la cámara">
            {errorGeneral}
          </Aviso>
        )}
        <CamposCamara valores={valores} errores={errores} cambiar={cambiar} conCodigo />
        <div className="formulario__pie">
          <Boton type="submit" variante="primario" icono={Plus} cargando={peticion.cargando} textoCargando="Creando…">
            Crear cámara
          </Boton>
          <BotonEnlace to="/camaras" variante="texto">
            Cancelar
          </BotonEnlace>
        </div>
      </form>

      {creada && (
        <DialogoToken nombre={creada.camara.nombre} token={creada.token} motivo="creada" onCerrar={cerrarToken} />
      )}
      {dialogoSalida}
    </>
  )
}

/** Solo lo que cambió: PATCH pide al menos un dato (minProperties: 1). */
function soloCambios(camara: Dispositivo, valores: Valores): DispositivoCambios {
  const cambios: DispositivoCambios = {}
  const nombre = limpiarNombre(valores.nombre)
  const url = valores.url.trim() || null
  if (nombre !== camara.nombre) cambios.nombre = nombre
  if (valores.tipo !== camara.tipo) cambios.tipo = valores.tipo
  if (url !== camara.url_captura) cambios.url_captura = url
  if (valores.activo !== camara.activo) cambios.activo = valores.activo
  return cambios
}

function FichaCamara({ camara }: { camara: Dispositivo }) {
  const inicial = valoresDe(camara)
  const [valores, setValores] = useState(inicial)
  const [errores, setErrores] = useState<Errores<CampoCamara>>({})
  const [errorGeneral, setErrorGeneral] = useState<string>()
  const [aviso, setAviso] = useState<string>()
  const editar = useEditarCamara()
  const formulario = useRef<HTMLFormElement>(null)
  const guardado = useRef(false)
  const sucio = JSON.stringify(soloCambios(camara, valores)) !== '{}'
  const dialogoSalida = usarSalidaProtegida(sucio, guardado)

  // Cambiar el token: primero se confirma; el token nuevo vive solo aquí mientras su diálogo está abierto.
  const peticion = usePeticionConToken()
  const [confirmarToken, setConfirmarToken] = useState(false)
  const [errorToken, setErrorToken] = useState<string>()
  const [tokenNuevo, setTokenNuevo] = useState<CamaraConToken | null>(null)
  const botonToken = useRef<HTMLButtonElement>(null)

  function cambiar<Clave extends keyof Valores>(clave: Clave, valor: Valores[Clave]) {
    setValores((actuales) => ({ ...actuales, [clave]: valor }))
    setAviso(undefined)
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const encontrados = validarCamara({ nombre: valores.nombre, tipo: valores.tipo, url: valores.url })
    setErrores(encontrados)
    setErrorGeneral(undefined)
    if (hayErrores(encontrados)) {
      enfocarPrimerError(formulario.current)
      return
    }
    const cambios = soloCambios(camara, valores)
    if (Object.keys(cambios).length === 0) {
      setAviso('No había cambios por guardar.')
      return
    }
    editar.mutate(
      { codigo: camara.codigo, cambios },
      {
        onSuccess: (guardada) => {
          setValores(valoresDe(guardada))
          setAviso('Cambios guardados.')
        },
        onError: (fallo) => {
          const { campo, mensaje } = ubicarError(fallo, false)
          if (campo) {
            setErrores({ [campo]: mensaje })
            enfocarPrimerError(formulario.current)
          } else {
            setErrorGeneral(mensaje)
          }
        },
      },
    )
  }

  async function cambiarToken() {
    setErrorToken(undefined)
    try {
      const resultado = await peticion.ejecutar(pedirTokenNuevo(camara.codigo))
      setConfirmarToken(false)
      setTokenNuevo(resultado)
    } catch (fallo) {
      setErrorToken(detalleDe(fallo))
    }
  }

  function cerrarToken() {
    setTokenNuevo(null)
    setAviso('Token cambiado. El anterior ya no sirve.')
    // El diálogo desaparece: el foco vuelve al botón que lo abrió.
    requestAnimationFrame(() => botonToken.current?.focus())
  }

  return (
    <>
      <Link className="miga" to="/camaras">
        <ArrowLeft aria-hidden />
        Cámaras
      </Link>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>{camara.nombre}</h1>
          <p className="encabezado__resumen">
            Código{' '}
            <span className="mono" translate="no">
              {camara.codigo}
            </span>{' '}
            · {NOMBRES_TIPO[camara.tipo]}
          </p>
        </div>
      </div>

      <div className="estado-accion" role="status">
        {aviso && <Aviso tono={aviso.startsWith('No había') ? 'info' : 'ok'}>{aviso}</Aviso>}
      </div>

      <div className="ficha">
        <form ref={formulario} className="formulario" onSubmit={enviar} noValidate aria-labelledby="titulo-datos-camara">
          <h2 id="titulo-datos-camara" className="visualmente-oculto">
            Datos de la cámara
          </h2>
          {errorGeneral && (
            <Aviso tono="error" rol="alert" titulo="No se pudieron guardar los cambios">
              {errorGeneral}
            </Aviso>
          )}
          <CamposCamara valores={valores} errores={errores} cambiar={cambiar} conCodigo={false} />
          <div className="formulario__pie">
            <Boton type="submit" variante="primario" icono={Save} cargando={editar.isPending} textoCargando="Guardando…">
              Guardar cambios
            </Boton>
          </div>
        </form>

        <div className="ficha__columna">
          <EstadoCamara camara={camara} />
          <section className="panel seccion" aria-labelledby="titulo-token">
            <div className="seccion__cabeza">
              <h2 id="titulo-token">Token</h2>
            </div>
            <p className="texto-secundario">
              Se mostró una sola vez, al crear la cámara o al cambiarlo. Si se perdió o alguien más lo conoce, cámbialo:
              el anterior deja de servir.
            </p>
            <div className="botones">
              <Boton
                ref={botonToken}
                variante="peligro-suave"
                icono={KeyRound}
                onClick={() => {
                  setErrorToken(undefined)
                  setConfirmarToken(true)
                }}
              >
                Cambiar token
              </Boton>
            </div>
          </section>
        </div>
      </div>

      <DialogoConfirmacion
        abierto={confirmarToken}
        titulo={`¿Cambiar el token de ${camara.nombre}?`}
        textoConfirmar="Cambiar token"
        textoCargando="Cambiando…"
        ocupado={peticion.cargando}
        error={errorToken}
        onConfirmar={() => void cambiarToken()}
        onCerrar={() => setConfirmarToken(false)}
      >
        <p>
          El token actual deja de servir de inmediato: <strong>la cámara no podrá enviar recortes</strong> hasta que le
          pongas el nuevo.
        </p>
      </DialogoConfirmacion>
      {tokenNuevo && (
        <DialogoToken nombre={camara.nombre} token={tokenNuevo.token} motivo="cambiado" onCerrar={cerrarToken} />
      )}
      {dialogoSalida}
    </>
  )
}

/** Conexión y modo, que cambian solos (la ficha se refresca cada 5 s). */
function EstadoCamara({ camara }: { camara: Dispositivo }) {
  const inscripcion = camara.inscripcion_activa
  const ahora = usarAhora(Boolean(inscripcion))
  return (
    <section className="panel seccion" aria-labelledby="titulo-estado-camara">
      <div className="seccion__cabeza">
        <h2 id="titulo-estado-camara">Estado</h2>
      </div>
      <dl className="datos">
        <dt>Conexión</dt>
        <dd>
          {camara.en_linea ? (
            <InsigniaEstado tono="ok" icono={Wifi}>
              En línea
            </InsigniaEstado>
          ) : (
            <InsigniaEstado tono="neutro" icono={WifiOff}>
              Sin conexión
            </InsigniaEstado>
          )}
        </dd>
        <dt>Último contacto</dt>
        <dd>{camara.ultimo_contacto ? formatearFechaHora(camara.ultimo_contacto) : 'Sin contacto todavía'}</dd>
        <dt>Modo</dt>
        <dd>
          {inscripcion ? (
            <>
              <InsigniaEstado tono="aviso" icono={ScanFace}>
                Inscribiendo
              </InsigniaEstado>
              <div className="tabla__secundario numeros">
                Muestra {inscripcion.muestras} de {inscripcion.requeridas} · vence en{' '}
                {formatearRestante(restanteHasta(inscripcion.vence, ahora))}
              </div>
              <Link to={`/inscripcion/${inscripcion.id}`}>Ver la inscripción</Link>
            </>
          ) : (
            'Reconoce'
          )}
        </dd>
        <dt>Creada</dt>
        <dd>{formatearFechaHora(camara.creado)}</dd>
      </dl>
    </section>
  )
}

function CamaraNoDisponible({ error, reintentar }: { error: unknown; reintentar: () => void }) {
  if (error instanceof ErrorApi && error.estado === 404) {
    return (
      <div className="panel">
        <Vacio
          icono={Cctv}
          titulo="Esa cámara no existe"
          acciones={
            <BotonEnlace to="/camaras" icono={ArrowLeft}>
              Volver a Cámaras
            </BotonEnlace>
          }
        >
          Revisa el código en la lista de cámaras.
        </Vacio>
      </div>
    )
  }
  return (
    <Aviso
      tono="error"
      rol="alert"
      titulo="No se pudo cargar la cámara"
      accion={
        <Boton icono={RotateCw} onClick={reintentar}>
          Reintentar
        </Boton>
      }
    >
      {detalleDe(error)}
    </Aviso>
  )
}
