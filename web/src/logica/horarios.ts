/**
 * Nombre: horarios.ts
 * Descripción: Resumen en español de los bloques de un horario (D-20): agrupa los días con la misma hora y tolerancia.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { components } from '../api/esquema'

type Bloque = components['schemas']['HorarioBloque']

/** 1 = lunes … 7 = domingo, como HorarioBloque.dia. */
const DIAS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'] as const

function nombreDia(dia: number): string {
  return DIAS[dia - 1] ?? `día ${dia}`
}

/** «lun, mar y jue»: une una lista con comas y una «y» al final. */
function unir(partes: string[]): string {
  if (partes.length <= 1) return partes.join('')
  return `${partes.slice(0, -1).join(', ')} y ${partes.at(-1)}`
}

/** Días seguidos de tres o más se escriben como rango: «lun a vie». */
function describirDias(dias: number[]): string {
  const tramos: number[][] = []
  for (const dia of dias) {
    const ultimo = tramos.at(-1)
    if (ultimo && dia === (ultimo.at(-1) ?? 0) + 1) ultimo.push(dia)
    else tramos.push([dia])
  }
  const partes = tramos.flatMap((tramo) =>
    tramo.length >= 3
      ? [`${nombreDia(tramo[0] ?? 0)} a ${nombreDia(tramo.at(-1) ?? 0)}`]
      : tramo.map(nombreDia),
  )
  return unir(partes)
}

/** «10 min» va con espacio duro: el número y la unidad no se parten de línea. */
function describirTolerancia(minutos: number): string {
  return minutos === 0 ? 'sin tolerancia' : `tolerancia de ${minutos}\u00a0min`
}

/**
 * «Lun a vie, 07:00, tolerancia de 10 min» o, con horas distintas por día,
 * «Lun, 07:00, tolerancia de 10 min; mié, 18:00, tolerancia de 15 min».
 */
export function resumirBloques(bloques: readonly Bloque[]): string {
  if (bloques.length === 0) return 'Sin bloques'
  const grupos = new Map<string, { hora: string; tolerancia: number; dias: number[] }>()
  for (const bloque of [...bloques].sort((a, b) => a.dia - b.dia)) {
    const clave = `${bloque.hora_inicio}|${bloque.tolerancia_min}`
    const grupo = grupos.get(clave)
    if (grupo) grupo.dias.push(bloque.dia)
    else grupos.set(clave, { hora: bloque.hora_inicio, tolerancia: bloque.tolerancia_min, dias: [bloque.dia] })
  }
  const texto = [...grupos.values()]
    .map((grupo) => `${describirDias(grupo.dias)}, ${grupo.hora}, ${describirTolerancia(grupo.tolerancia)}`)
    .join('; ')
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}
