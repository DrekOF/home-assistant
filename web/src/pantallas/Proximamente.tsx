/**
 * Nombre: Proximamente.tsx
 * Descripción: Pantallas que todavía no existen (Accesos, Asistencia y Horarios, del Día 3): dicen qué harán.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import { Aviso } from '../componentes/Aviso'
import { usarTitulo } from '../componentes/titulo'

export type SeccionProxima = 'accesos' | 'asistencia' | 'horarios'

const SECCIONES: Record<SeccionProxima, { titulo: string; resumen: string; hara: string[] }> = {
  accesos: {
    titulo: 'Accesos',
    resumen: 'El registro de cada intento de entrada: quién, cuándo, por qué cámara y con qué resultado.',
    hara: ['Filtrar por fecha, cámara y resultado.', 'Ver por qué se negó una entrada.'],
  },
  asistencia: {
    titulo: 'Asistencia',
    resumen: 'El reporte del día: a tiempo, tarde, sin horario y ausentes.',
    hara: [
      'Registrar a mano la llegada de quien no dio su consentimiento, o si la cámara falla.',
      'Ver las llegadas de cualquier día.',
    ],
  },
  horarios: {
    titulo: 'Horarios',
    resumen: 'Los horarios por bloques: un renglón por día con su hora de entrada y su tolerancia.',
    hara: ['Crear, editar y borrar horarios.', 'Ver qué personas usan cada horario.'],
  },
}

export function Proximamente({ seccion }: { seccion: SeccionProxima }) {
  const { titulo, resumen, hara } = SECCIONES[seccion]
  usarTitulo(titulo)

  return (
    <>
      <div className="encabezado">
        <div className="encabezado__texto">
          <h1>{titulo}</h1>
          <p className="encabezado__resumen">{resumen}</p>
        </div>
      </div>
      <section className="panel proximamente" aria-labelledby="titulo-proximamente">
        <Aviso tono="info" titulo="Próximamente">
          Esta pantalla está en construcción.
        </Aviso>
        <div>
          <h2 id="titulo-proximamente" className="aviso__titulo">
            Lo que podrás hacer aquí
          </h2>
          <ul className="proximamente__lista">
            {hara.map((linea) => (
              <li key={linea}>{linea}</li>
            ))}
          </ul>
        </div>
      </section>
    </>
  )
}
