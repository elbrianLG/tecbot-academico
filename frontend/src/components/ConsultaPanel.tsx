/**
 * Panel mínimo de consulta académica.
 *
 * Consume `POST /api/consulta` con timeout de 12 s, valida localmente la
 * pregunta y traduce los errores HTTP a mensajes en español sin exponer el
 * `detail` crudo de FastAPI.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { ConsultaResponse } from '../types/consulta'

export const MAX_PREGUNTA = 1000
export const TIEMPO_LIMITE_MS = 12_000

const MENSAJE_VALIDACION = 'Escribe una pregunta antes de consultar.'
const MENSAJE_ERROR_RED =
  'No se pudo conectar con el servicio. Revisa tu conexión e intenta de nuevo.'
const MENSAJE_TIMEOUT =
  'La consulta tardó más de 12 segundos. Intenta de nuevo.'
const MENSAJE_RESPUESTA_INVALIDA =
  'El servicio devolvió una respuesta inesperada. Intenta de nuevo.'
const MENSAJE_ERROR_GENERICO =
  'No se pudo completar la consulta. Intenta de nuevo.'

const MENSAJES_POR_ESTADO: Record<number, string> = {
  422: 'La pregunta no es válida. Revisa el texto e intenta de nuevo.',
  503: 'El servicio no tiene documentos disponibles en este momento. Intenta más tarde.',
  504: 'El servicio tardó demasiado en responder. Intenta de nuevo.',
  500: 'Ocurrió un error en el servidor. Intenta de nuevo más tarde.',
}

type Estado = 'inicial' | 'cargando' | 'exito' | 'error'

function esRespuestaValida(datos: unknown): datos is ConsultaResponse {
  if (typeof datos !== 'object' || datos === null) return false
  const posible = datos as Partial<ConsultaResponse>
  return (
    typeof posible.respuesta === 'string' &&
    Array.isArray(posible.fuentes) &&
    (posible.advertencia === null || typeof posible.advertencia === 'string')
  )
}

function ConsultaPanel() {
  const [pregunta, setPregunta] = useState('')
  const [estado, setEstado] = useState<Estado>('inicial')
  const [resultado, setResultado] = useState<ConsultaResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  async function manejarEnvio(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()

    const preguntaLimpia = pregunta.trim()
    if (preguntaLimpia.length === 0) {
      setErrorValidacion(MENSAJE_VALIDACION)
      return
    }

    setErrorValidacion(null)
    setEstado('cargando')
    setResultado(null)
    setError(null)

    const controlador = new AbortController()
    abortRef.current = controlador
    const idTimeout = setTimeout(() => controlador.abort(), TIEMPO_LIMITE_MS)
    timeoutRef.current = idTimeout

    try {
      const respuesta = await fetch('/api/consulta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pregunta: preguntaLimpia }),
        signal: controlador.signal,
      })

      if (!respuesta.ok) {
        setError(MENSAJES_POR_ESTADO[respuesta.status] ?? MENSAJE_ERROR_GENERICO)
        setEstado('error')
        return
      }

      const datos: unknown = await respuesta.json()
      if (!esRespuestaValida(datos)) {
        setError(MENSAJE_RESPUESTA_INVALIDA)
        setEstado('error')
        return
      }

      setResultado(datos)
      setEstado('exito')
    } catch (fallo) {
      const nombre = (fallo as { name?: string } | null)?.name
      setError(nombre === 'AbortError' ? MENSAJE_TIMEOUT : MENSAJE_ERROR_RED)
      setEstado('error')
    } finally {
      clearTimeout(idTimeout)
      if (timeoutRef.current === idTimeout) {
        timeoutRef.current = null
      }
      if (abortRef.current === controlador) {
        abortRef.current = null
      }
    }
  }

  const cargando = estado === 'cargando'

  return (
    <div className="consulta-panel">
      <form className="consulta-form" onSubmit={manejarEnvio} noValidate>
        <label className="consulta-label" htmlFor="pregunta-academica">
          Tu pregunta
        </label>

        <textarea
          id="pregunta-academica"
          className="consulta-input"
          value={pregunta}
          onChange={(evento) => {
            setPregunta(evento.target.value)
            if (errorValidacion !== null) {
              setErrorValidacion(null)
            }
          }}
          maxLength={MAX_PREGUNTA}
          rows={4}
          placeholder="Ej. ¿Qué necesito para el servicio social?"
          aria-describedby="contador-pregunta"
          disabled={cargando}
        />

        <div className="consulta-meta">
          <span id="contador-pregunta" className="consulta-contador">
            {pregunta.length}/{MAX_PREGUNTA}
          </span>
          <button
            type="submit"
            className="btn-primary consulta-boton"
            disabled={cargando}
          >
            {cargando ? 'Consultando…' : 'Consultar'}
          </button>
        </div>
      </form>

      {errorValidacion !== null && (
        <p className="consulta-error-validacion" role="alert">
          {errorValidacion}
        </p>
      )}

      <div className="consulta-resultado" aria-live="polite">
        {estado === 'inicial' && (
          <p className="consulta-ayuda">
            Escribe una pregunta sobre servicio social, residencias,
            titulación o acreditación.
          </p>
        )}

        {estado === 'cargando' && (
          <p className="consulta-cargando" role="status">
            Consultando documentos…
          </p>
        )}

        {estado === 'error' && error !== null && (
          <p className="consulta-error" role="alert">
            {error}
          </p>
        )}

        {estado === 'exito' && resultado !== null && (
          <article className="consulta-respuesta">
            <h3>Respuesta</h3>
            <p className="consulta-texto">{resultado.respuesta}</p>

            {resultado.fuentes.length > 0 ? (
              <div className="consulta-fuentes">
                <h4>Fuentes</h4>
                <ul>
                  {resultado.fuentes.map((fuente, indice) => (
                    <li key={`${fuente.documento}-${indice}`}>
                      <span className="fuente-documento">
                        {fuente.documento}
                      </span>
                      <p className="fuente-fragmento">{fuente.fragmento}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="consulta-sin-fuentes">
                No se citaron fuentes documentales.
              </p>
            )}

            {resultado.advertencia !== null && (
              <p className="consulta-advertencia" role="note">
                {resultado.advertencia}
              </p>
            )}
          </article>
        )}
      </div>
    </div>
  )
}

export default ConsultaPanel
