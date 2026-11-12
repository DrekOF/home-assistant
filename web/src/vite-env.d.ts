/**
 * Nombre: vite-env.d.ts
 * Descripción: Tipos del entorno de Vite que usa la web de AccesIA.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** «1» activa el simulacro de la API con MSW (npm run dev:simulacro). */
  readonly VITE_SIMULACRO?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/** true si la web corre con el simulacro; Vite lo reemplaza al compilar (vite.config.ts, define). */
declare const __SIMULACRO__: boolean
