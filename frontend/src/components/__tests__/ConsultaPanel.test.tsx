import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConsultaPanel from '../ConsultaPanel'

const fetchMock = vi.fn()

const RESPUESTA_CON_FUENTES = {
  respuesta:
    'Para iniciar el servicio social necesitas cumplir con los requisitos del documento.',
  fuentes: [
    {
      documento: 'servicio-social.md',
      fragmento: 'Requisitos de demostración para el servicio social.',
    },
  ],
  advertencia:
    'Consulta los canales oficiales de la institución para confirmar la información.',
}

describe('ConsultaPanel', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('no envía la consulta cuando la pregunta está vacía o solo tiene espacios', async () => {
    const user = userEvent.setup()
    render(<ConsultaPanel />)

    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Escribe una pregunta antes de consultar.',
    )
    expect(fetchMock).not.toHaveBeenCalled()

    await user.type(screen.getByLabelText('Tu pregunta'), '   ')
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Escribe una pregunta antes de consultar.',
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('muestra la respuesta, las fuentes y la advertencia', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => RESPUESTA_CON_FUENTES,
    })

    const user = userEvent.setup()
    render(<ConsultaPanel />)

    await user.type(
      screen.getByLabelText('Tu pregunta'),
      '  ¿Qué necesito para el servicio social?  ',
    )
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(
      await screen.findByText(RESPUESTA_CON_FUENTES.respuesta),
    ).toBeInTheDocument()
    expect(screen.getByText('servicio-social.md')).toBeInTheDocument()
    expect(
      screen.getByText(RESPUESTA_CON_FUENTES.fuentes[0].fragmento),
    ).toBeInTheDocument()
    expect(
      screen.getByText(RESPUESTA_CON_FUENTES.advertencia),
    ).toBeInTheDocument()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/consulta',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          pregunta: '¿Qué necesito para el servicio social?',
        }),
      }),
    )
  })

  it('muestra un mensaje en español para el error 503 sin exponer el detail', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'detalle interno del servidor' }),
    })

    const user = userEvent.setup()
    render(<ConsultaPanel />)

    await user.type(
      screen.getByLabelText('Tu pregunta'),
      '¿Cuáles son las modalidades de titulación?',
    )
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(
      await screen.findByText(
        'El servicio no tiene documentos disponibles en este momento. Intenta más tarde.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText(/detalle interno del servidor/)).not.toBeInTheDocument()
  })

  it.each<[number, string]>([
    [422, 'La pregunta no es válida. Revisa el texto e intenta de nuevo.'],
    [504, 'El servicio tardó demasiado en responder. Intenta de nuevo.'],
    [500, 'Ocurrió un error en el servidor. Intenta de nuevo más tarde.'],
  ])('traduce el error %i a un mensaje en español', async (estado, mensaje) => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: estado,
      json: async () => ({ error: 'codigo', mensaje: 'detalle interno' }),
    })

    const user = userEvent.setup()
    render(<ConsultaPanel />)

    await user.type(screen.getByLabelText('Tu pregunta'), 'Pregunta de prueba')
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(await screen.findByText(mensaje)).toBeInTheDocument()
    expect(screen.queryByText(/detalle interno/)).not.toBeInTheDocument()
  })

  it('muestra un mensaje cuando falla la conexión de red', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    const user = userEvent.setup()
    render(<ConsultaPanel />)

    await user.type(screen.getByLabelText('Tu pregunta'), 'Pregunta de prueba')
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(
      await screen.findByText(
        'No se pudo conectar con el servicio. Revisa tu conexión e intenta de nuevo.',
      ),
    ).toBeInTheDocument()
  })
})
