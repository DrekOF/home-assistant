/**
 * Nombre: consultas.ts
 * Descripción: Consultas y cambios de la API con TanStack Query: sesión, personas, consentimiento y horarios.
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import {
  api,
  ErrorApi,
  exigir,
  type ConsentimientoNuevo,
  type Esquemas,
  type Persona,
  type PersonaCambios,
  type PersonaNueva,
} from './cliente'

export type FiltrosPersonas = { q: string; activa?: boolean; pagina: number; porPagina: number }

export const claves = {
  sesion: ['sesion'] as const,
  personas: ['personas'] as const,
  listaPersonas: (filtros: FiltrosPersonas) => ['personas', 'lista', filtros] as const,
  persona: (id: string) => ['personas', 'ficha', id] as const,
  consentimiento: (id: string) => ['consentimiento', id] as const,
  consentimientos: (id: string) => ['consentimientos', id] as const,
  textoConsentimiento: ['texto-consentimiento'] as const,
  horarios: ['horarios'] as const,
}

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
