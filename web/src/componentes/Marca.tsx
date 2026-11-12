/**
 * Nombre: Marca.tsx
 * Descripción: Símbolo de AccesIA: una puerta dentro del marco de enfoque de una cámara.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

/** fondo y trazo permiten usarlo sobre el panel de color del inicio de sesión. */
export function Marca({ fondo = '#0b5e78', trazo = '#ffffff' }: { fondo?: string; trazo?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden focusable="false">
      <rect width="32" height="32" rx="7" fill={fondo} />
      <g fill="none" stroke={trazo} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M7 12V8.5A1.5 1.5 0 0 1 8.5 7H12M20 7h3.5A1.5 1.5 0 0 1 25 8.5V12M25 20v3.5a1.5 1.5 0 0 1-1.5 1.5H20M12 25H8.5A1.5 1.5 0 0 1 7 23.5V20" />
        <path d="M12.5 22v-9.5a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1V22" />
      </g>
      <circle cx="17.6" cy="17" r="1.1" fill={trazo} />
    </svg>
  )
}
