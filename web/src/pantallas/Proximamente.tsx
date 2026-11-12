/**
 * Nombre: Proximamente.tsx
 * Descripción: Pantallas que todavía no existen: dicen qué harán. Inscripción muestra cómo se verá su barra de avance.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { useSearchParams } from 'react-router'
import { usePersona } from '../api/consultas'
import { Aviso } from '../componentes/Aviso'
import { BarraAvance } from '../componentes/BarraAvance'
import { usarTitulo } from '../componentes/titulo'

export type SeccionProxima = 'inscripcion' | 'accesos' | 'asistencia' | 'camaras' | 'horarios'

const SECCIONES: Record<SeccionProxima, { titulo: string; resumen: string; hara: string[] }> = {
  inscripcion: {
    titulo: 'Inscripción',
    resumen: 'Inscribe a una persona con la cámara: cada cara válida se guarda como una muestra.',
    hara: [
      'Elegir a la persona, que debe tener consentimiento vigente, y la cámara.',
      'Ver el avance en vivo, muestra por muestra, y el motivo del último rechazo.',
      'Cancelar una inscripción activa.',
    ],
  },
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
  camaras: {
    titulo: 'Cámaras',
    resumen: 'Las cámaras registradas, si están en línea y en qué modo trabajan.',
    hara: ['Crear una cámara y ver su token una sola vez.', 'Activar, desactivar o cambiar el token de una cámara.'],
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
  const [parametros] = useSearchParams()
  const persona = usePersona(seccion === 'inscripcion' ? (parametros.get('persona') ?? undefined) : undefined)

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
        {persona.data && (
          <p>
            Cuando esté lista, la inscripción empezará con <strong>{persona.data.nombre}</strong>.
          </p>
        )}
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
        {seccion === 'inscripcion' && (
          <div className="proximamente__muestra">
            <p className="proximamente__muestra-titulo">Vista previa del avance</p>
            <BarraAvance actual={3} total={5} />
          </div>
        )}
      </section>
    </>
  )
}
