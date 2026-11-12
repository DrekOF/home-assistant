/**
 * Nombre: manejadores.ts
 * Descripción: Simulacro de la API con MSW: sesión, personas, consentimiento, horarios, cámaras e inscripciones, con los códigos de error del contrato.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import { delay, http, HttpResponse } from 'msw'
import type {
  CodigoError,
  Consentimiento,
  ConsentimientoNuevo,
  Dispositivo,
  DispositivoCambios,
  DispositivoConToken,
  DispositivoNuevo,
  Esquemas,
  Inscripcion,
  InscripcionCorta,
  InscripcionNueva,
  PaginaPersonas,
  Persona,
  PersonaCambios,
  PersonaNueva,
  Rol,
  TipoCamara,
} from '../api/cliente'
import { esFutura, isoColombia } from '../logica/fechas'
import { coincide } from '../logica/texto'
import {
  CODIGO_RESERVADO,
  esUrlCaptura,
  NOMBRE_CAMARA_MAX,
  NOMBRE_CAMARA_MIN,
  NOMBRE_MAX,
  NOMBRE_MIN,
  PATRON_CODIGO_CAMARA,
  PATRON_DOCUMENTO,
} from '../logica/validaciones'
import { textoConsentimiento } from './consentimiento'
import {
  CREDENCIALES_SIMULACRO,
  crearEstado,
  GUION,
  MUESTRAS_REQUERIDAS,
  PASO_MS,
  VENCE_MS,
  type CamaraGuardada,
  type InscripcionGuardada,
  type PersonaGuardada,
} from './datos'

// «*» acepta cualquier origen: la misma ruta sirve en el navegador y en las pruebas con Node.
const API = '*/api/v1'
const ROLES: Rol[] = ['estudiante', 'docente', 'administrativo', 'otro']
const TIPOS: TipoCamara[] = ['tinyml', 'respaldo', 'simulador']
/** Como el servidor: una cámara está en línea si su último contacto fue hace 2 minutos o menos. */
const EN_LINEA_MS = 2 * 60 * 1000
const PATRON_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

let estado = crearEstado()

/** Vuelve a los datos de ejemplo y cierra la sesión. */
export function reiniciarSimulacro(): void {
  estado = crearEstado()
}

function error(status: number, codigo: CodigoError, detalle: string) {
  return HttpResponse.json<Esquemas['Error']>({ codigo, detalle }, { status })
}

const sinSesion = () => error(401, 'sin_sesion', 'Inicia sesión para continuar.')
const personaNoExiste = () => error(404, 'no_encontrado', 'Esa persona no existe o ya fue borrada.')
const camaraNoExiste = (codigo: string) => error(404, 'no_encontrado', `No hay una cámara con el código ${codigo}.`)
const inscripcionNoExiste = () => error(404, 'no_encontrado', 'Esa inscripción no existe.')
const validacion = (detalle: string) => error(422, 'validacion', detalle)

/** Como el servidor: «Los datos no son válidos: revisa «codigo», «nombre».», más la frase de la regla que falló. */
function datosInvalidos(campos: string[], frase?: string) {
  const revisa = campos.length ? `: revisa ${[...campos].sort().map((campo) => `«${campo}»`).join(', ')}` : ''
  return validacion([`Los datos no son válidos${revisa}.`, frase].filter(Boolean).join(' '))
}

/** Una pausa corta en el navegador, como la de una red real: deja ver los estados de carga. En las pruebas, ninguna. */
const pausa = () => delay(typeof window === 'undefined' ? 0 : 180)

async function leerJson(request: Request): Promise<Record<string, unknown> | null> {
  try {
    const cuerpo: unknown = await request.json()
    return cuerpo !== null && typeof cuerpo === 'object' && !Array.isArray(cuerpo) ? (cuerpo as Record<string, unknown>) : null
  } catch {
    return null
  }
}

function vigenteDe(personaId: string): Consentimiento | undefined {
  return estado.consentimientos.find((c) => c.persona_id === personaId && c.revocado_en === null)
}

function aPersona(guardada: PersonaGuardada): Persona {
  const horario = estado.horarios.find((h) => h.id === guardada.horario_id)
  return {
    ...guardada,
    horario_nombre: horario?.nombre ?? null,
    consentimiento_vigente: vigenteDe(guardada.id) !== undefined,
  }
}

const iso = (milisegundos: number) => isoColombia(new Date(milisegundos))

function activaDe(codigo: string): InscripcionGuardada | undefined {
  return estado.inscripciones.find((i) => i.dispositivo === codigo && i.estado === 'activa')
}

/**
 * Pone al día una inscripción activa: aplica los pasos del guion que ya llegaron (solo si su cámara está
 * activa y en línea, porque si no, no llegan caras) y, si ya pasó su hora, la vence (R9).
 */
function alDia(inscripcion: InscripcionGuardada, ahora = Date.now()): void {
  if (inscripcion.estado !== 'activa') return
  const camara = estado.camaras.find((c) => c.codigo === inscripcion.dispositivo)
  if (camara?.activo && camara.conectada) {
    const debidos = Math.floor((Math.min(ahora, inscripcion.vence) - inscripcion.creada) / PASO_MS)
    while (inscripcion.pasos < debidos && inscripcion.estado === 'activa') {
      const paso = GUION[inscripcion.pasos]
      if (paso === undefined) break
      inscripcion.pasos += 1
      if (paso !== 'aceptada') {
        // R7: el rechazo deja su motivo; una muestra aceptada después no lo borra, como en el servidor.
        inscripcion.ultimo_motivo = paso
        continue
      }
      inscripcion.muestras += 1
      const persona = estado.personas.find((p) => p.id === inscripcion.persona_id)
      if (persona) persona.muestras += 1
      if (inscripcion.muestras >= inscripcion.requeridas) {
        inscripcion.estado = 'completada'
        inscripcion.terminada = inscripcion.creada + inscripcion.pasos * PASO_MS
      }
    }
  }
  if (inscripcion.estado === 'activa' && ahora >= inscripcion.vence) {
    inscripcion.estado = 'vencida'
    inscripcion.terminada = inscripcion.vence
  }
}

/** R9: el vencimiento se revisa al consultar la inscripción, al abrir otra y al listar o ver las cámaras. */
function todasAlDia(ahora = Date.now()): void {
  for (const inscripcion of estado.inscripciones) alDia(inscripcion, ahora)
}

function aInscripcion(guardada: InscripcionGuardada): Inscripcion {
  const persona = estado.personas.find((p) => p.id === guardada.persona_id)
  return {
    id: guardada.id,
    persona: { id: guardada.persona_id, nombre: persona?.nombre ?? '' },
    dispositivo: guardada.dispositivo,
    estado: guardada.estado,
    muestras: guardada.muestras,
    requeridas: guardada.requeridas,
    ultimo_motivo: guardada.ultimo_motivo,
    creada: iso(guardada.creada),
    vence: iso(guardada.vence),
    terminada: guardada.terminada === null ? null : iso(guardada.terminada),
  }
}

function aCorta(guardada: InscripcionGuardada): InscripcionCorta {
  return {
    id: guardada.id,
    muestras: guardada.muestras,
    requeridas: guardada.requeridas,
    estado: guardada.estado,
    vence: iso(guardada.vence),
  }
}

/** modo es inscribir si y solo si inscripcion_activa no es null (Dispositivo en openapi.yaml). */
function aDispositivo(guardada: CamaraGuardada, ahora = Date.now()): Dispositivo {
  const { conectada, ...datos } = guardada
  // Una cámara conectada envía todo el tiempo: su último contacto es de hace unos segundos.
  const ultimoContacto = conectada ? iso(ahora - 3000) : guardada.ultimo_contacto
  const activa = activaDe(guardada.codigo)
  return {
    ...datos,
    ultimo_contacto: ultimoContacto,
    en_linea: ultimoContacto !== null && ahora - Date.parse(ultimoContacto) <= EN_LINEA_MS,
    modo: activa ? 'inscribir' : 'reconocer',
    inscripcion_activa: activa ? aCorta(activa) : null,
  }
}

/** Como el del servidor: 32 bytes aleatorios en base64 para URL, 43 caracteres. */
function tokenNuevo(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32))
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

/** Revisa los campos de DispositivoNuevo (`nueva`) o DispositivoCambios; null si están bien. */
function revisarCamara(cuerpo: Record<string, unknown>, nueva: boolean) {
  const { codigo, nombre, tipo, url_captura, activo } = cuerpo
  const campos: string[] = []
  if (nueva && (typeof codigo !== 'string' || !PATRON_CODIGO_CAMARA.test(codigo))) campos.push('codigo')
  if (nueva || nombre !== undefined) {
    const largo = typeof nombre === 'string' ? nombre.trim().length : 0
    if (largo < NOMBRE_CAMARA_MIN || largo > NOMBRE_CAMARA_MAX) campos.push('nombre')
  }
  if ((nueva || tipo !== undefined) && !TIPOS.includes(tipo as TipoCamara)) campos.push('tipo')
  if (url_captura !== undefined && url_captura !== null && (typeof url_captura !== 'string' || !esUrlCaptura(url_captura))) {
    campos.push('url_captura')
  }
  if (!nueva && activo !== undefined && typeof activo !== 'boolean') campos.push('activo')
  if (campos.length) return datosInvalidos(campos)
  if (nueva && codigo === CODIGO_RESERVADO) {
    return datosInvalidos([], 'El código «servidor» está reservado para los temas MQTT del servidor.')
  }
  return null
}

/** Revisa los campos de PersonaNueva o PersonaCambios; devuelve el detalle del primer problema. */
function revisarCampos(cuerpo: Record<string, unknown>, id?: string): { codigo: CodigoError; detalle: string } | null {
  const { documento, nombre, rol, horario_id, activa } = cuerpo
  if (documento !== undefined) {
    if (typeof documento !== 'string' || !PATRON_DOCUMENTO.test(documento)) {
      return { codigo: 'validacion', detalle: 'El documento debe tener de 3 a 20 letras, números o guiones.' }
    }
    if (estado.personas.some((p) => p.documento === documento && p.id !== id)) {
      return { codigo: 'documento_duplicado', detalle: `Ya hay una persona con el documento ${documento}.` }
    }
  }
  if (nombre !== undefined) {
    const largo = typeof nombre === 'string' ? nombre.trim().length : 0
    if (largo < NOMBRE_MIN || largo > NOMBRE_MAX) {
      return { codigo: 'validacion', detalle: `El nombre debe tener de ${NOMBRE_MIN} a ${NOMBRE_MAX} caracteres.` }
    }
  }
  if (rol !== undefined && !ROLES.includes(rol as Rol)) {
    return { codigo: 'validacion', detalle: 'El rol debe ser estudiante, docente, administrativo u otro.' }
  }
  if (horario_id !== undefined && horario_id !== null && !estado.horarios.some((h) => h.id === horario_id)) {
    return { codigo: 'validacion', detalle: 'Ese horario no existe.' }
  }
  if (activa !== undefined && typeof activa !== 'boolean') {
    return { codigo: 'validacion', detalle: 'activa debe ser verdadero o falso.' }
  }
  return null
}

export const manejadores = [
  http.post(`${API}/sesion`, async ({ request }) => {
    await pausa()
    const cuerpo = await leerJson(request)
    const correo = typeof cuerpo?.correo === 'string' ? cuerpo.correo.trim().toLowerCase() : ''
    const clave = typeof cuerpo?.clave === 'string' ? cuerpo.clave : ''
    if (!correo || clave.length < 8) return validacion('Escribe el correo y una clave de al menos 8 caracteres.')
    if (correo !== CREDENCIALES_SIMULACRO.correo || clave !== CREDENCIALES_SIMULACRO.clave) {
      return error(401, 'credenciales_invalidas', 'El correo o la clave no coinciden. Revísalos e intenta de nuevo.')
    }
    estado.sesion = true
    return HttpResponse.json(estado.administrador)
  }),

  http.get(`${API}/sesion`, async () => {
    await pausa()
    return estado.sesion ? HttpResponse.json(estado.administrador) : sinSesion()
  }),

  http.delete(`${API}/sesion`, async () => {
    await pausa()
    estado.sesion = false
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${API}/personas`, async ({ request }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const parametros = new URL(request.url).searchParams
    const q = parametros.get('q') ?? ''
    const activa = parametros.get('activa')
    const pagina = Number(parametros.get('pagina') ?? '1')
    const porPagina = Number(parametros.get('por_pagina') ?? '20')
    if (q.length > 60) return validacion('La búsqueda puede tener hasta 60 caracteres.')
    if (activa !== null && activa !== 'true' && activa !== 'false') return validacion('activa debe ser true o false.')
    if (!Number.isInteger(pagina) || pagina < 1) return validacion('pagina debe ser un entero desde 1.')
    if (!Number.isInteger(porPagina) || porPagina < 1 || porPagina > 100) {
      return validacion('por_pagina debe ser un entero de 1 a 100.')
    }
    const filtradas = estado.personas
      .filter((p) => coincide(q, p.nombre, p.documento))
      .filter((p) => activa === null || p.activa === (activa === 'true'))
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
    const cuerpo: PaginaPersonas = {
      elementos: filtradas.slice((pagina - 1) * porPagina, pagina * porPagina).map(aPersona),
      total: filtradas.length,
      pagina,
      por_pagina: porPagina,
    }
    return HttpResponse.json(cuerpo)
  }),

  http.post(`${API}/personas`, async ({ request }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const cuerpo = await leerJson(request)
    if (!cuerpo || typeof cuerpo.documento !== 'string' || typeof cuerpo.nombre !== 'string') {
      return validacion('Faltan el documento o el nombre.')
    }
    const problema = revisarCampos(cuerpo)
    if (problema) return error(problema.codigo === 'documento_duplicado' ? 409 : 422, problema.codigo, problema.detalle)
    const nueva = cuerpo as PersonaNueva
    const ahora = isoColombia()
    const guardada: PersonaGuardada = {
      id: crypto.randomUUID(),
      documento: nueva.documento,
      nombre: nueva.nombre.trim(),
      rol: nueva.rol ?? 'estudiante',
      horario_id: nueva.horario_id ?? null,
      activa: nueva.activa ?? true,
      muestras: 0,
      creada: ahora,
      actualizada: ahora,
    }
    estado.personas.push(guardada)
    return HttpResponse.json(aPersona(guardada), { status: 201 })
  }),

  http.get(`${API}/personas/:personaId`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.personas.find((p) => p.id === params.personaId)
    return guardada ? HttpResponse.json(aPersona(guardada)) : personaNoExiste()
  }),

  http.patch(`${API}/personas/:personaId`, async ({ params, request }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.personas.find((p) => p.id === params.personaId)
    if (!guardada) return personaNoExiste()
    const cuerpo = await leerJson(request)
    if (!cuerpo || Object.keys(cuerpo).length === 0) return validacion('Envía al menos un dato para cambiar.')
    const problema = revisarCampos(cuerpo, guardada.id)
    if (problema) return error(problema.codigo === 'documento_duplicado' ? 409 : 422, problema.codigo, problema.detalle)
    const cambios = cuerpo as PersonaCambios
    if (cambios.documento !== undefined) guardada.documento = cambios.documento
    if (cambios.nombre !== undefined) guardada.nombre = cambios.nombre.trim()
    if (cambios.rol !== undefined) guardada.rol = cambios.rol
    if (cambios.horario_id !== undefined) guardada.horario_id = cambios.horario_id
    if (cambios.activa !== undefined) guardada.activa = cambios.activa
    guardada.actualizada = isoColombia()
    return HttpResponse.json(aPersona(guardada))
  }),

  http.get(`${API}/personas/:personaId/consentimiento`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    if (!estado.personas.some((p) => p.id === params.personaId)) return personaNoExiste()
    return HttpResponse.json(vigenteDe(String(params.personaId)) ?? null)
  }),

  http.post(`${API}/personas/:personaId/consentimiento`, async ({ params, request }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.personas.find((p) => p.id === params.personaId)
    if (!guardada) return personaNoExiste()
    const cuerpo = (await leerJson(request)) as Partial<ConsentimientoNuevo> | null
    if (!cuerpo || cuerpo.acepta !== true) return validacion('El consentimiento necesita que la persona acepte (acepta: true).')
    if (cuerpo.version_texto !== textoConsentimiento.version) {
      return error(
        422,
        'version_texto_invalida',
        `El texto vigente es la versión ${textoConsentimiento.version}. Recarga la ficha y muéstrale a la persona el texto actual.`,
      )
    }
    const medio = cuerpo.medio ?? 'web'
    if (medio !== 'web' && medio !== 'papel') return validacion('El medio debe ser web o papel.')
    if (vigenteDe(guardada.id)) {
      return error(409, 'consentimiento_vigente', 'Esta persona ya tiene un consentimiento vigente.')
    }
    let aceptadoEn = isoColombia()
    // Con papel, aceptado_en es la hora de la firma; con web, o si falta, la hora del registro.
    if (medio === 'papel' && cuerpo.aceptado_en !== undefined) {
      if (Number.isNaN(Date.parse(cuerpo.aceptado_en))) return validacion('aceptado_en no es una fecha válida.')
      if (esFutura(cuerpo.aceptado_en)) return validacion('La fecha de la firma no puede ser futura.')
      aceptadoEn = cuerpo.aceptado_en
    }
    const nuevo: Consentimiento = {
      id: crypto.randomUUID(),
      persona_id: guardada.id,
      version_texto: textoConsentimiento.version,
      medio,
      registrado_por: estado.administrador.nombre,
      aceptado_en: aceptadoEn,
      revocado_en: null,
    }
    estado.consentimientos.push(nuevo)
    guardada.actualizada = isoColombia()
    return HttpResponse.json(nuevo, { status: 201 })
  }),

  http.delete(`${API}/personas/:personaId/consentimiento`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.personas.find((p) => p.id === params.personaId)
    const vigente = guardada ? vigenteDe(guardada.id) : undefined
    if (!guardada || !vigente) return error(404, 'no_encontrado', 'La persona no existe o no tiene un consentimiento vigente.')
    // RF-02 · C5: revocar borra las huellas y cancela la inscripción activa, todo junto.
    const ahora = Date.now()
    todasAlDia(ahora)
    for (const inscripcion of estado.inscripciones) {
      if (inscripcion.persona_id === guardada.id && inscripcion.estado === 'activa') {
        inscripcion.estado = 'cancelada'
        inscripcion.terminada = ahora
      }
    }
    vigente.revocado_en = iso(ahora)
    guardada.muestras = 0
    guardada.actualizada = vigente.revocado_en
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${API}/personas/:personaId/consentimientos`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    if (!estado.personas.some((p) => p.id === params.personaId)) return personaNoExiste()
    const lista = estado.consentimientos
      .filter((c) => c.persona_id === params.personaId)
      .sort((a, b) => Date.parse(b.aceptado_en) - Date.parse(a.aceptado_en))
    return HttpResponse.json(lista)
  }),

  http.get(`${API}/consentimiento/texto`, async () => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    return HttpResponse.json(textoConsentimiento)
  }),

  http.get(`${API}/horarios`, async () => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    return HttpResponse.json(estado.horarios)
  }),

  http.get(`${API}/dispositivos`, async () => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const ahora = Date.now()
    todasAlDia(ahora)
    const ordenadas = [...estado.camaras].sort((a, b) => (a.codigo < b.codigo ? -1 : 1))
    return HttpResponse.json(ordenadas.map((camara) => aDispositivo(camara, ahora)))
  }),

  http.post(`${API}/dispositivos`, async ({ request }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const cuerpo = await leerJson(request)
    if (!cuerpo) return datosInvalidos([], 'Revisa el cuerpo de la petición.')
    const problema = revisarCamara(cuerpo, true)
    if (problema) return problema
    const nueva = cuerpo as DispositivoNuevo
    const url = nueva.url_captura ?? null
    if (nueva.tipo === 'respaldo' && url === null) {
      return datosInvalidos([], 'Una cámara de respaldo necesita su URL de captura.')
    }
    if (estado.camaras.some((c) => c.codigo === nueva.codigo)) {
      return error(409, 'codigo_duplicado', `Ya hay una cámara con el código ${nueva.codigo}.`)
    }
    const guardada: CamaraGuardada = {
      codigo: nueva.codigo,
      nombre: nueva.nombre.trim(),
      tipo: nueva.tipo,
      url_captura: url,
      activo: true,
      conectada: false,
      ultimo_contacto: null,
      estado: null,
      creado: isoColombia(),
    }
    estado.camaras.push(guardada)
    // El token sale solo en esta respuesta: el simulacro no lo guarda, como el servidor guarda solo su hash.
    const conToken: DispositivoConToken = { ...aDispositivo(guardada), token: tokenNuevo() }
    return HttpResponse.json(conToken, { status: 201 })
  }),

  http.get(`${API}/dispositivos/:codigo`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.camaras.find((c) => c.codigo === params.codigo)
    if (!guardada) return camaraNoExiste(String(params.codigo))
    const ahora = Date.now()
    todasAlDia(ahora)
    return HttpResponse.json(aDispositivo(guardada, ahora))
  }),

  http.patch(`${API}/dispositivos/:codigo`, async ({ params, request }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.camaras.find((c) => c.codigo === params.codigo)
    if (!guardada) return camaraNoExiste(String(params.codigo))
    const cuerpo = await leerJson(request)
    if (!cuerpo || Object.keys(cuerpo).length === 0) return validacion('Envía al menos un dato para cambiar.')
    const problema = revisarCamara(cuerpo, false)
    if (problema) return problema
    const cambios = cuerpo as DispositivoCambios
    const tipo = cambios.tipo ?? guardada.tipo
    const url = cambios.url_captura !== undefined ? cambios.url_captura : guardada.url_captura
    if (tipo === 'respaldo' && url === null) return validacion('Una cámara de respaldo necesita su URL de captura.')
    if (cambios.nombre !== undefined) guardada.nombre = cambios.nombre.trim()
    guardada.tipo = tipo
    guardada.url_captura = url
    if (cambios.activo !== undefined) guardada.activo = cambios.activo
    const ahora = Date.now()
    todasAlDia(ahora)
    return HttpResponse.json(aDispositivo(guardada, ahora))
  }),

  http.post(`${API}/dispositivos/:codigo/token`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.camaras.find((c) => c.codigo === params.codigo)
    if (!guardada) return camaraNoExiste(String(params.codigo))
    const conToken: DispositivoConToken = { ...aDispositivo(guardada), token: tokenNuevo() }
    return HttpResponse.json(conToken)
  }),

  http.post(`${API}/inscripciones`, async ({ request }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const cuerpo = await leerJson(request)
    if (!cuerpo) return datosInvalidos([], 'Revisa el cuerpo de la petición.')
    const campos: string[] = []
    if (typeof cuerpo.persona_id !== 'string' || !PATRON_UUID.test(cuerpo.persona_id)) campos.push('persona_id')
    if (typeof cuerpo.dispositivo !== 'string' || !PATRON_CODIGO_CAMARA.test(cuerpo.dispositivo)) campos.push('dispositivo')
    if (campos.length) return datosInvalidos(campos)
    const { persona_id, dispositivo } = cuerpo as InscripcionNueva
    // El mismo orden del servidor: persona, cámara, cámara activa, consentimiento y una sola activa por cámara.
    const persona = estado.personas.find((p) => p.id === persona_id)
    if (!persona) return personaNoExiste()
    const camara = estado.camaras.find((c) => c.codigo === dispositivo)
    if (!camara) return camaraNoExiste(dispositivo)
    if (!camara.activo) return validacion('La cámara está desactivada: actívala antes de inscribir.')
    if (!vigenteDe(persona.id)) {
      return error(422, 'sin_consentimiento', 'La persona no tiene un consentimiento vigente: regístralo antes de inscribirla.')
    }
    const ahora = Date.now()
    todasAlDia(ahora)
    if (activaDe(dispositivo)) {
      return error(409, 'inscripcion_activa', `Ya hay una inscripción activa en la cámara ${dispositivo}.`)
    }
    const nueva: InscripcionGuardada = {
      id: crypto.randomUUID(),
      persona_id: persona.id,
      dispositivo,
      estado: 'activa',
      muestras: 0,
      requeridas: MUESTRAS_REQUERIDAS,
      ultimo_motivo: null,
      creada: ahora,
      vence: ahora + VENCE_MS,
      terminada: null,
      pasos: 0,
    }
    estado.inscripciones.push(nueva)
    return HttpResponse.json(aInscripcion(nueva), { status: 201 })
  }),

  http.get(`${API}/inscripciones/:inscripcionId`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.inscripciones.find((i) => i.id === params.inscripcionId)
    if (!guardada) return inscripcionNoExiste()
    alDia(guardada)
    return HttpResponse.json(aInscripcion(guardada))
  }),

  http.delete(`${API}/inscripciones/:inscripcionId`, async ({ params }) => {
    await pausa()
    if (!estado.sesion) return sinSesion()
    const guardada = estado.inscripciones.find((i) => i.id === params.inscripcionId)
    if (!guardada) return inscripcionNoExiste()
    const ahora = Date.now()
    alDia(guardada, ahora)
    if (guardada.estado !== 'activa') {
      return error(409, 'inscripcion_terminada', 'Esa inscripción ya terminó: no se puede cancelar.')
    }
    // Las muestras aceptadas se conservan (RF-03 · C4).
    guardada.estado = 'cancelada'
    guardada.terminada = ahora
    return new HttpResponse(null, { status: 204 })
  }),

  // El resto del contrato llega con sus pantallas: el simulacro responde con el esquema Error.
  http.all(`${API}/*`, async () => {
    await pausa()
    return error(404, 'no_encontrado', 'El simulacro todavía no atiende esta ruta: llega con su pantalla.')
  }),
]
