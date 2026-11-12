/**
 * Nombre: InicioSesion.tsx
 * Descripción: Pantalla de inicio de sesión de los administradores (RF-09 · C1).
 * Fecha de creación: 2026-11-11
 * Actualización: 2026-11-11
 * Autor: Equipo AccesIA
 * Versión: 1.0
 */

import { LogIn } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { detalleDe } from '../api/cliente'
import { useIniciarSesion, useSesion } from '../api/consultas'
import { Aviso } from '../componentes/Aviso'
import { Boton } from '../componentes/Boton'
import { Campo, enfocarPrimerError } from '../componentes/Campo'
import { Marca } from '../componentes/Marca'
import { usarTitulo } from '../componentes/titulo'
import { hayErrores, validarCredenciales, type Errores } from '../logica/validaciones'
import { destinoSeguro } from '../sesion'
import { CREDENCIALES_SIMULACRO } from '../simulacro/credenciales'

export function InicioSesion() {
  usarTitulo('Entrar')
  const sesion = useSesion()
  const iniciar = useIniciarSesion()
  const navegar = useNavigate()
  const [parametros] = useSearchParams()
  const destino = destinoSeguro(parametros.get('siguiente'))
  const formulario = useRef<HTMLFormElement>(null)
  const [correo, setCorreo] = useState('')
  const [clave, setClave] = useState('')
  const [errores, setErrores] = useState<Errores<'correo' | 'clave'>>({})

  if (sesion.data) return <Navigate to={destino} replace />

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const encontrados = validarCredenciales({ correo, clave })
    setErrores(encontrados)
    if (hayErrores(encontrados)) {
      enfocarPrimerError(formulario.current)
      return
    }
    iniciar.mutate(
      { correo: correo.trim(), clave },
      { onSuccess: () => navegar(destino, { replace: true, state: { desdeEntrada: true } }) },
    )
  }

  return (
    <div className="entrada">
      <section className="entrada__marca" aria-label="Sobre AccesIA">
        <p className="entrada__logo">
          <Marca fondo="#ffffff" trazo="#0b5e78" />
          <span translate="no">AccesIA</span>
        </p>
        <p className="entrada__lema">Control de acceso y asistencia con reconocimiento facial.</p>
        <p className="entrada__pie">
          Proyecto de Inteligencia Artificial de la Universidad Surcolombiana. Solo se guardan huellas de 128 números,
          nunca fotos de caras, y solo de quien dio su consentimiento.
        </p>
      </section>
      <main className="entrada__formulario">
        <div className="entrada__panel">
          <div className="encabezado__texto">
            <h1>Entrar</h1>
            <p className="encabezado__resumen">Administración de AccesIA</p>
          </div>

          {__SIMULACRO__ && (
            <Aviso tono="aviso" titulo="Simulacro">
              <div className="credenciales-demo">
                <p>Los datos son de ejemplo. Entra con:</p>
                <dl>
                  <dt>Correo</dt>
                  <dd className="mono">{CREDENCIALES_SIMULACRO.correo}</dd>
                  <dt>Clave</dt>
                  <dd className="mono">{CREDENCIALES_SIMULACRO.clave}</dd>
                </dl>
              </div>
            </Aviso>
          )}

          {iniciar.isError && (
            <Aviso tono="error" rol="alert">
              {detalleDe(iniciar.error)}
            </Aviso>
          )}

          <form ref={formulario} onSubmit={enviar} noValidate>
            <Campo etiqueta="Correo" error={errores.correo}>
              {(control) => (
                <input
                  {...control}
                  className="control"
                  type="email"
                  name="correo"
                  autoComplete="username"
                  spellCheck={false}
                  autoFocus
                  placeholder="nombre@dominio.co…"
                  value={correo}
                  onChange={(evento) => setCorreo(evento.target.value)}
                />
              )}
            </Campo>
            <Campo etiqueta="Clave" error={errores.clave}>
              {(control) => (
                <input
                  {...control}
                  className="control"
                  type="password"
                  name="clave"
                  autoComplete="current-password"
                  value={clave}
                  onChange={(evento) => setClave(evento.target.value)}
                />
              )}
            </Campo>
            <Boton type="submit" variante="primario" icono={LogIn} cargando={iniciar.isPending} textoCargando="Entrando…">
              Entrar
            </Boton>
          </form>
        </div>
      </main>
    </div>
  )
}
