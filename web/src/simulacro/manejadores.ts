/**
 * Nombre: manejadores.ts
 * Descripción: Simulacro de la API con MSW: sesión, personas, consentimiento y horarios, con los códigos de error del contrato.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { delay, http, HttpResponse } from 'msw'
import type {
  CodigoError,
  Consentimiento,
  ConsentimientoNuevo,
  Esquemas,
  PaginaPersonas,
  Persona,
  PersonaCambios,
  PersonaNueva,
  Rol,
} from '../api/cliente'
import { esFutura, isoColombia } from '../logica/fechas'
import { coincide } from '../logica/texto'
import { NOMBRE_MAX, NOMBRE_MIN, PATRON_DOCUMENTO } from '../logica/validaciones'
import { textoConsentimiento } from './consentimiento'
import { CREDENCIALES_SIMULACRO, crearEstado, type PersonaGuardada } from './datos'

// «*» acepta cualquier origen: la misma ruta sirve en el navegador y en las pruebas con Node.
const API = '*/api/v1'
const ROLES: Rol[] = ['estudiante', 'docente', 'administrativo', 'otro']

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
const validacion = (detalle: string) => error(422, 'validacion', detalle)

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
    vigente.revocado_en = isoColombia()
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

  // El resto del contrato llega con sus pantallas: el simulacro responde con el esquema Error.
  http.all(`${API}/*`, async () => {
    await pausa()
    return error(404, 'no_encontrado', 'El simulacro todavía no atiende esta ruta: llega con su pantalla.')
  }),
]
