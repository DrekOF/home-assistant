/**
 * Nombre: texto.ts
 * Descripción: Utilidades de texto: comparar sin tildes ni mayúsculas y leer el Markdown sencillo del consentimiento.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

/** Minúsculas y sin tildes: «Óscar Núñez» queda «oscar nunez». */
export function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim()
}

/** Si la búsqueda aparece en alguno de los campos, sin importar tildes ni mayúsculas. */
export function coincide(busqueda: string, ...campos: string[]): boolean {
  const buscado = normalizar(busqueda)
  if (!buscado) return true
  return campos.some((campo) => normalizar(campo).includes(buscado))
}

export type Fragmento = { negrita: boolean; texto: string }

/**
 * Parte el texto del consentimiento en párrafos (separados por una línea en blanco) y cada párrafo en
 * fragmentos normales o en **negrita**. Solo eso: el texto se muestra como texto, nunca como HTML.
 */
export function leerParrafos(markdown: string): Fragmento[][] {
  return markdown
    .replace(/\r\n/g, '\n')
    .split(/\n\s*\n/)
    .map((parrafo) => parrafo.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean)
    .map((parrafo) =>
      parrafo
        .split(/(\*\*[^*]+\*\*)/)
        .filter(Boolean)
        .map((parte) =>
          parte.startsWith('**') && parte.endsWith('**')
            ? { negrita: true, texto: parte.slice(2, -2) }
            : { negrita: false, texto: parte },
        ),
    )
}
