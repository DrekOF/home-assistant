/**
 * Nombre: datos.ts
 * Descripción: Datos de ejemplo del simulacro, coherentes con el contrato 1.2: personas ficticias, horarios por bloques y consentimientos.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import type { Administrador, Consentimiento, Horario, Persona, Rol } from '../api/cliente'
import { CREDENCIALES_SIMULACRO } from './credenciales'

export { CREDENCIALES_SIMULACRO }

/** Lo que el simulacro guarda de una persona; horario_nombre, consentimiento_vigente salen al responder. */
export type PersonaGuardada = Omit<Persona, 'horario_nombre' | 'consentimiento_vigente'>

export type EstadoSimulacro = {
  sesion: boolean
  administrador: Administrador
  horarios: Horario[]
  personas: PersonaGuardada[]
  consentimientos: Consentimiento[]
}

/** UUID fijos para que las direcciones de los datos de ejemplo no cambien entre recargas. */
const uuid = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`

const ADMINISTRADOR: Administrador = { id: uuid(900), correo: CREDENCIALES_SIMULACRO.correo, nombre: 'Administrador de prueba' }

const CLASE_IA = uuid(101)
const MANANA = uuid(102)
const SABADOS = uuid(103)

const HORARIOS: Horario[] = [
  {
    id: CLASE_IA,
    nombre: 'Clase de IA',
    bloques: [
      { dia: 1, hora_inicio: '07:00', tolerancia_min: 10 },
      { dia: 3, hora_inicio: '18:00', tolerancia_min: 15 },
    ],
  },
  {
    id: MANANA,
    nombre: 'Jornada de la mañana',
    bloques: [1, 2, 3, 4, 5].map((dia) => ({ dia, hora_inicio: '07:00', tolerancia_min: 10 })),
  },
  { id: SABADOS, nombre: 'Sábados', bloques: [{ dia: 6, hora_inicio: '08:00', tolerancia_min: 15 }] },
]

type Fila = [n: number, nombre: string, documento: string, rol: Rol, horario: string | null, activa: boolean, muestras: number, creada: string]

// Personas ficticias. Las muestras son huellas: solo las tiene quien dio su consentimiento.
const FILAS: Fila[] = [
  [1, 'Ana María Gómez Rojas', '1075234567', 'estudiante', CLASE_IA, true, 5, '2026-11-02T08:14:00-05:00'],
  [2, 'Carlos Andrés Ramírez Polanía', '1075198220', 'estudiante', MANANA, true, 5, '2026-11-02T08:20:00-05:00'],
  [3, 'Laura Valentina Cuéllar Díaz', '1004567321', 'estudiante', CLASE_IA, true, 0, '2026-11-03T10:02:00-05:00'],
  [4, 'Andrés Felipe Trujillo Vargas', '7712345', 'docente', CLASE_IA, true, 5, '2026-11-03T10:30:00-05:00'],
  [5, 'Diana Marcela Ortiz Charry', '36178455', 'administrativo', MANANA, true, 3, '2026-11-04T09:12:00-05:00'],
  [6, 'Santiago Muñoz Losada', '1077850012', 'estudiante', null, true, 0, '2026-11-04T11:40:00-05:00'],
  [7, 'Valentina Ospina Cerquera', '1075301944', 'estudiante', CLASE_IA, true, 0, '2026-11-05T14:05:00-05:00'],
  [8, 'Juan Sebastián Rojas Quintero', '1075277310', 'estudiante', MANANA, false, 5, '2026-11-05T15:22:00-05:00'],
  [9, 'Paula Andrea Medina Castro', '55162784', 'docente', SABADOS, true, 0, '2026-11-06T08:45:00-05:00'],
  [10, 'Óscar Iván Cabrera Silva', 'CE-482913', 'otro', null, false, 0, '2026-11-06T09:10:00-05:00'],
  [11, 'Natalia Hernández Polo', '1003945110', 'estudiante', CLASE_IA, true, 5, '2026-11-09T16:30:00-05:00'],
  [12, 'Esteban Calderón Núñez', '1075412876', 'estudiante', MANANA, true, 0, '2026-11-10T07:50:00-05:00'],
]

const PERSONAS: PersonaGuardada[] = FILAS.map(([n, nombre, documento, rol, horario_id, activa, muestras, creada]) => ({
  id: uuid(n),
  documento,
  nombre,
  rol,
  horario_id,
  activa,
  muestras,
  creada,
  actualizada: creada,
}))

const consentimiento = (
  n: number,
  persona: number,
  medio: Consentimiento['medio'],
  aceptado_en: string,
  revocado_en: string | null = null,
): Consentimiento => ({
  id: uuid(n),
  persona_id: uuid(persona),
  version_texto: '1.0',
  medio,
  registrado_por: ADMINISTRADOR.nombre,
  aceptado_en,
  revocado_en,
})

const CONSENTIMIENTOS: Consentimiento[] = [
  consentimiento(201, 1, 'web', '2026-11-02T08:16:00-05:00'),
  consentimiento(202, 2, 'papel', '2026-11-01T17:40:00-05:00'),
  consentimiento(204, 4, 'web', '2026-11-03T10:33:00-05:00'),
  consentimiento(205, 5, 'papel', '2026-11-04T08:55:00-05:00'),
  // Valentina lo dio y después lo revocó: su historial muestra los dos estados.
  consentimiento(207, 7, 'web', '2026-11-05T14:08:00-05:00', '2026-11-09T11:20:00-05:00'),
  consentimiento(208, 8, 'web', '2026-11-05T15:25:00-05:00'),
  consentimiento(211, 11, 'web', '2026-11-09T16:34:00-05:00'),
]

/** Un estado nuevo, copiado de los datos de ejemplo: el simulacro vive en memoria y se reinicia al recargar. */
export function crearEstado(): EstadoSimulacro {
  return structuredClone({
    sesion: false,
    administrador: ADMINISTRADOR,
    horarios: HORARIOS,
    personas: PERSONAS,
    consentimientos: CONSENTIMIENTOS,
  })
}
