/**
 * Nombre: inscripcion.ts
 * Descripción: Textos y cálculos de la inscripción: qué dice cada motivo de rechazo (R7), el tiempo que falta hasta que vence (R9) y su estado.
 * Fecha de creación: 2026-11-12
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { EstadoInscripcion, MotivoMuestra } from '../api/cliente'

export type TextoMotivo = {
  /** Qué pasó con la muestra. */
  que: string
  /** Qué hacer para que la siguiente sí sirva. */
  hacer: string
}

/**
 * Un texto por cada MotivoMuestra del contrato (R7). Ninguno dice a quién se parece la cara,
 * ni siquiera con parece_otra_persona (RNF-01 · C3).
 */
export const MOTIVOS: Record<MotivoMuestra, TextoMotivo> = {
  sin_cara: {
    que: 'No se vio ninguna cara.',
    hacer: 'Mira de frente a la cámara, con la cara bien iluminada.',
  },
  varias_caras: {
    que: 'Había más de una cara frente a la cámara.',
    hacer: 'Que frente a la cámara quede solo la persona que se inscribe.',
  },
  cara_pequena: {
    que: 'La cara se ve muy pequeña.',
    hacer: 'Acércate a la cámara.',
  },
  borrosa: {
    que: 'La imagen salió borrosa.',
    hacer: 'Quédate quieto un momento frente a la cámara.',
  },
  parece_otra_persona: {
    que: 'La cara se parece a la de otra persona ya inscrita.',
    hacer: 'Revisa que sea la persona correcta y que no esté inscrita con otro nombre.',
  },
  distinta_de_la_primera: {
    que: 'La cara no se parece a la de la primera muestra.',
    hacer: 'Que solo mire la cámara quien se inscribe. Si la primera muestra salió mal, cancela y abre otra inscripción.',
  },
}

export const NOMBRES_ESTADO: Record<EstadoInscripcion, string> = {
  activa: 'En curso',
  completada: 'Completada',
  vencida: 'Vencida',
  cancelada: 'Cancelada',
}

/** «1 muestra», «3 muestras». */
export function contarMuestras(cantidad: number): string {
  return cantidad === 1 ? '1 muestra' : `${cantidad} muestras`
}

/** Qué pasa con las muestras al cancelar o vencer (RF-03 · C4): se conservan las aceptadas, si hay. */
export function textoConservadas(cantidad: number): string {
  if (cantidad === 0) return 'No hay muestras aceptadas.'
  if (cantidad === 1) return 'La muestra aceptada se conserva.'
  return `Las ${cantidad} muestras aceptadas se conservan.`
}

/** Milisegundos que faltan hasta `vence`; negativo si ya pasó. */
export function restanteHasta(vence: string, ahora: number): number {
  return Date.parse(vence) - ahora
}

/**
 * «1:42»: minutos y segundos que faltan, nunca negativo. Redondea hacia arriba, para que no
 * se vea 0:00 mientras todavía queda una fracción de segundo.
 */
export function formatearRestante(milisegundos: number): string {
  const segundos = Math.max(0, Math.ceil(milisegundos / 1000))
  return `${Math.floor(segundos / 60)}:${String(segundos % 60).padStart(2, '0')}`
}
