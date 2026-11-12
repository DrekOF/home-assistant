/**
 * Nombre: consultas.ts
 * Descripción: Consultas y cambios de la API con TanStack Query: sesión, personas, consentimiento, horarios, cámaras e inscripciones.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-12
 * Autor: Equipo AccesIA
 * Versión: 1.1
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import {
  api,
  ErrorApi,
  exigir,
  type ConsentimientoNuevo,
  type Dispositivo,
  type DispositivoCambios,
  type DispositivoConToken,
  type Esquemas,
  type InscripcionNueva,
  type Persona,
  type PersonaCambios,
  type PersonaNueva,
} from './cliente'

export type FiltrosPersonas = { q: string; activa?: boolean; pagina: number; porPagina: number }

export const claves = {
  sesion: ['sesion'] as const,
  personas: ['personas'] as const,
  listaPersonas: (filtros: FiltrosPersonas) => ['personas', 'lista', filtros] as const,
  // Bajo «lista»: se vuelve a pedir cuando cambia una persona o su consentimiento.
  personasConConsentimiento: ['personas', 'lista', 'con-consentimiento'] as const,
  persona: (id: string) => ['personas', 'ficha', id] as const,
  consentimiento: (id: string) => ['consentimiento', id] as const,
  consentimientos: (id: string) => ['consentimientos', id] as const,
  textoConsentimiento: ['texto-consentimiento'] as const,
  horarios: ['horarios'] as const,
  camaras: ['camaras'] as const,
  camara: (codigo: string) => ['camaras', 'ficha', codigo] as const,
  inscripcion: (id: string) => ['inscripciones', id] as const,
}

/** La lista de cámaras se refresca sola: en línea, último contacto y la inscripción en curso cambian sin avisar. */
export const REFRESCO_CAMARAS_MS = 5000
/** RF-03 · C6: la web consulta la inscripción cada segundo mientras está activa. */
export const REFRESCO_INSCRIPCION_MS = 1000

const ruta = (id: string) => ({ params: { path: { persona_id: id } } })

/** El administrador de la sesión, o null si no hay sesión (401). */
export function useSesion() {
  return useQuery({
    queryKey: claves.sesion,
    queryFn: async () => {
      try {
        return await exigir(api.GET('/api/v1/sesion'))
      } catch (error) {
        if (error instanceof ErrorApi && error.estado === 401) return null
        throw error
      }
    },
    staleTime: Infinity,
    retry: false,
  })
}

export function useIniciarSesion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (credenciales: Esquemas['Credenciales']) => exigir(api.POST('/api/v1/sesion', { body: credenciales })),
    onSuccess: (administrador) => cliente.setQueryData(claves.sesion, administrador),
  })
}

export function useCerrarSesion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: () => exigir(api.DELETE('/api/v1/sesion')),
    onSettled: () => {
      // Al salir no queda nada de las personas en la memoria del navegador.
      cliente.clear()
      cliente.setQueryData(claves.sesion, null)
    },
  })
}

export function usePersonas(filtros: FiltrosPersonas) {
  return useQuery({
    queryKey: claves.listaPersonas(filtros),
    queryFn: () =>
      exigir(
        api.GET('/api/v1/personas', {
          params: {
            query: {
              q: filtros.q || undefined,
              activa: filtros.activa,
              pagina: filtros.pagina,
              por_pagina: filtros.porPagina,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })
}

export function usePersona(id: string | undefined) {
  return useQuery({
    queryKey: claves.persona(id ?? ''),
    queryFn: () => exigir(api.GET('/api/v1/personas/{persona_id}', ruta(id ?? ''))),
    enabled: Boolean(id),
  })
}

export function useConsentimiento(id: string) {
  return useQuery({
    queryKey: claves.consentimiento(id),
    queryFn: () => exigir(api.GET('/api/v1/personas/{persona_id}/consentimiento', ruta(id))),
  })
}

export function useConsentimientos(id: string) {
  return useQuery({
    queryKey: claves.consentimientos(id),
    queryFn: () => exigir(api.GET('/api/v1/personas/{persona_id}/consentimientos', ruta(id))),
  })
}

export function useTextoConsentimiento() {
  return useQuery({
    queryKey: claves.textoConsentimiento,
    queryFn: () => exigir(api.GET('/api/v1/consentimiento/texto')),
    staleTime: Infinity,
  })
}

export function useHorarios() {
  return useQuery({
    queryKey: claves.horarios,
    queryFn: () => exigir(api.GET('/api/v1/horarios')),
    staleTime: 5 * 60 * 1000,
  })
}

/** Después de cambiar una persona: su ficha queda al día y las listas se vuelven a pedir. */
function alDia(cliente: QueryClient, persona: Persona) {
  cliente.setQueryData(claves.persona(persona.id), persona)
  void cliente.invalidateQueries({ queryKey: [...claves.personas, 'lista'] })
}

export function useCrearPersona() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (datos: PersonaNueva) => exigir(api.POST('/api/v1/personas', { body: datos })),
    onSuccess: (persona) => alDia(cliente, persona),
  })
}

export function useEditarPersona() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ id, cambios }: { id: string; cambios: PersonaCambios }) =>
      exigir(api.PATCH('/api/v1/personas/{persona_id}', { ...ruta(id), body: cambios })),
    onSuccess: (persona) => alDia(cliente, persona),
  })
}

/** Consentimiento: al registrarlo o revocarlo cambian la ficha, el vigente, el historial y las listas. */
function refrescarConsentimiento(cliente: QueryClient, id: string) {
  return Promise.all([
    cliente.invalidateQueries({ queryKey: claves.persona(id) }),
    cliente.invalidateQueries({ queryKey: claves.consentimiento(id) }),
    cliente.invalidateQueries({ queryKey: claves.consentimientos(id) }),
    cliente.invalidateQueries({ queryKey: [...claves.personas, 'lista'] }),
  ])
}

export function useRegistrarConsentimiento(id: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (datos: ConsentimientoNuevo) =>
      exigir(api.POST('/api/v1/personas/{persona_id}/consentimiento', { ...ruta(id), body: datos })),
    onSuccess: () => refrescarConsentimiento(cliente, id),
  })
}

export function useRevocarConsentimiento(id: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: () => exigir(api.DELETE('/api/v1/personas/{persona_id}/consentimiento', ruta(id))),
    onSuccess: () => refrescarConsentimiento(cliente, id),
  })
}

/** Personas que se pueden inscribir: las que tienen consentimiento vigente (R9). El contrato no filtra por él. */
export function usePersonasConConsentimiento() {
  return useQuery({
    queryKey: claves.personasConConsentimiento,
    queryFn: async () => {
      const todas: Persona[] = []
      for (let pagina = 1; ; pagina += 1) {
        const datos = await exigir(api.GET('/api/v1/personas', { params: { query: { pagina, por_pagina: 100 } } }))
        todas.push(...datos.elementos)
        if (datos.elementos.length === 0 || todas.length >= datos.total) break
      }
      return todas
        .filter((persona) => persona.consentimiento_vigente)
        .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
    },
  })
}

// --- Cámaras (RF-10) ---

export function useCamaras() {
  return useQuery({
    queryKey: claves.camaras,
    queryFn: () => exigir(api.GET('/api/v1/dispositivos')),
    refetchInterval: REFRESCO_CAMARAS_MS,
  })
}

export function useCamara(codigo: string | undefined) {
  return useQuery({
    queryKey: claves.camara(codigo ?? ''),
    queryFn: () => exigir(api.GET('/api/v1/dispositivos/{codigo}', { params: { path: { codigo: codigo ?? '' } } })),
    enabled: Boolean(codigo),
    // La ficha muestra si está en línea y su modo: también se refresca sola.
    refetchInterval: REFRESCO_CAMARAS_MS,
  })
}

/** Después de cambiar una cámara: su ficha queda al día y la lista se vuelve a pedir. */
function camaraAlDia(cliente: QueryClient, camara: Dispositivo) {
  cliente.setQueryData(claves.camara(camara.codigo), camara)
  void cliente.invalidateQueries({ queryKey: claves.camaras, exact: true })
}

export function useEditarCamara() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ codigo, cambios }: { codigo: string; cambios: DispositivoCambios }) =>
      exigir(api.PATCH('/api/v1/dispositivos/{codigo}', { params: { path: { codigo } }, body: cambios })),
    onSuccess: (camara) => camaraAlDia(cliente, camara),
  })
}

export type CamaraConToken = { camara: Dispositivo; token: string }

/**
 * Crear una cámara y cambiar su token devuelven el token, que se muestra una sola vez (RF-10 · C1 y C2). Por eso
 * no usan TanStack Query: el token no pasa por ningún caché. La cámara, sin el token, sí queda al día.
 */
export function usePeticionConToken() {
  const cliente = useQueryClient()
  const [cargando, setCargando] = useState(false)

  /** Devuelve la cámara y su token, o lanza el error de la API para que quien llama lo muestre donde va. */
  const ejecutar = useCallback(
    async (peticion: () => Promise<DispositivoConToken>): Promise<CamaraConToken> => {
      setCargando(true)
      try {
        const { token, ...camara } = await peticion()
        camaraAlDia(cliente, camara)
        return { camara, token }
      } catch (fallo) {
        // Igual que en las consultas: si la sesión venció, la web vuelve al inicio de sesión.
        if (fallo instanceof ErrorApi && fallo.codigo === 'sin_sesion') cliente.setQueryData(claves.sesion, null)
        throw fallo
      } finally {
        setCargando(false)
      }
    },
    [cliente],
  )

  return { ejecutar, cargando }
}

export const pedirCamaraNueva = (datos: Esquemas['DispositivoNuevo']) => () =>
  exigir(api.POST('/api/v1/dispositivos', { body: datos }))

export const pedirTokenNuevo = (codigo: string) => () =>
  exigir(api.POST('/api/v1/dispositivos/{codigo}/token', { params: { path: { codigo } } }))

// --- Inscripciones (RF-03, R9) ---

/** Con `vivo`, la consulta cada segundo mientras está activa (RF-03 · C6); sin él, solo para saber de quién es. */
export function useInscripcion(id: string | undefined, { vivo = true }: { vivo?: boolean } = {}) {
  return useQuery({
    queryKey: claves.inscripcion(id ?? ''),
    queryFn: () =>
      exigir(api.GET('/api/v1/inscripciones/{inscripcion_id}', { params: { path: { inscripcion_id: id ?? '' } } })),
    enabled: Boolean(id),
    refetchInterval: (consulta) => (vivo && consulta.state.data?.estado === 'activa' ? REFRESCO_INSCRIPCION_MS : false),
  })
}

/** Al abrir o cancelar una inscripción cambian la cámara (modo e inscripción activa) y las muestras de la persona. */
function refrescarInscripcion(cliente: QueryClient, personaId?: string) {
  void cliente.invalidateQueries({ queryKey: claves.camaras })
  if (personaId) void cliente.invalidateQueries({ queryKey: claves.persona(personaId) })
}

export function useAbrirInscripcion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (datos: InscripcionNueva) => exigir(api.POST('/api/v1/inscripciones', { body: datos })),
    onSuccess: (inscripcion) => {
      cliente.setQueryData(claves.inscripcion(inscripcion.id), inscripcion)
      refrescarInscripcion(cliente, inscripcion.persona.id)
    },
  })
}

export function useCancelarInscripcion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string; personaId?: string }) =>
      exigir(api.DELETE('/api/v1/inscripciones/{inscripcion_id}', { params: { path: { inscripcion_id: id } } })),
    onSettled: (_, __, { id, personaId }) =>
      Promise.all([cliente.invalidateQueries({ queryKey: claves.inscripcion(id) }), refrescarInscripcion(cliente, personaId)]),
  })
}
