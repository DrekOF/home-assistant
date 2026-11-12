/**
 * Nombre: cliente.ts
 * Descripción: Cliente de la API de AccesIA con openapi-fetch y los tipos generados desde openapi.yaml.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import createClient from 'openapi-fetch'
import type { components, paths } from './esquema'

// Alias de los esquemas del contrato: salen de esquema.d.ts, que genera «npm run tipos».
export type Esquemas = components['schemas']
export type Administrador = Esquemas['Administrador']
export type Persona = Esquemas['Persona']
export type PersonaNueva = Esquemas['PersonaNueva']
export type PersonaCambios = Esquemas['PersonaCambios']
export type PaginaPersonas = Esquemas['PaginaPersonas']
export type Consentimiento = Esquemas['Consentimiento']
export type ConsentimientoNuevo = Esquemas['ConsentimientoNuevo']
export type TextoConsentimiento = Esquemas['TextoConsentimiento']
export type Horario = Esquemas['Horario']
export type Rol = Esquemas['Rol']
export type CodigoError = Esquemas['Error']['codigo']
export type Dispositivo = Esquemas['Dispositivo']
export type DispositivoNuevo = Esquemas['DispositivoNuevo']
export type DispositivoCambios = Esquemas['DispositivoCambios']
export type DispositivoConToken = Esquemas['DispositivoConToken']
export type TipoCamara = Esquemas['TipoCamara']
export type Inscripcion = Esquemas['Inscripcion']
export type InscripcionNueva = Esquemas['InscripcionNueva']
export type InscripcionCorta = Esquemas['InscripcionCorta']
export type EstadoInscripcion = Esquemas['EstadoInscripcion']
export type MotivoMuestra = Esquemas['MotivoMuestra']

/** Misma dirección que la web: la cookie de sesión viaja sola (HttpOnly, SameSite=Strict). */
export const api = createClient<paths>({ baseUrl: '' })

/** Un error de la API con su código del contrato, o sin_conexion si no hubo respuesta. */
export class ErrorApi extends Error {
  readonly estado: number
  readonly codigo: CodigoError | 'sin_conexion'

  constructor(estado: number, codigo: CodigoError | 'sin_conexion', detalle: string) {
    super(detalle)
    this.name = 'ErrorApi'
    this.estado = estado
    this.codigo = codigo
  }
}

type Respuesta<T> = { data?: T; error?: unknown; response: Response }

/** Espera la respuesta y devuelve sus datos; si la API respondió un error, lanza ErrorApi con su detalle. */
export async function exigir<T>(peticion: Promise<Respuesta<T>>): Promise<T> {
  let respuesta: Respuesta<T>
  try {
    respuesta = await peticion
  } catch {
    throw new ErrorApi(0, 'sin_conexion', 'No hay conexión con el servidor. Revisa que esté encendido e intenta de nuevo.')
  }
  const { data, error, response } = respuesta
  if (!response.ok) {
    const cuerpo = (error ?? {}) as Partial<Esquemas['Error']>
    throw new ErrorApi(
      response.status,
      cuerpo.codigo ?? 'error_interno',
      cuerpo.detalle ?? `El servidor respondió con el estado ${response.status}. Intenta de nuevo.`,
    )
  }
  return data as T
}

/** El detalle en español de cualquier error, para mostrarlo tal cual. */
export function detalleDe(error: unknown): string {
  if (error instanceof ErrorApi) return error.message
  return 'Algo salió mal. Intenta de nuevo.'
}
