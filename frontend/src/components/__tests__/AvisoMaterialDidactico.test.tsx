import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../../App'
import { AVISO_MATERIAL_DIDACTICO } from '../AvisoMaterialDidactico'

const fetchMock = vi.fn()

const RESPUESTA_EXITOSA = {
  respuesta: 'Necesitas cumplir con los requisitos indicados en el documento.',
  fuentes: [
    {
      documento: 'servicio-social.md',
      fragmento: 'Fragmento de demostración sobre requisitos.',
    },
  ],
  advertencia: null,
}

function respuestaOk(cuerpo: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => cuerpo,
  }
}

describe('AvisoMaterialDidactico', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('test_aviso_material_didactico permanece visible en inicial, cargando, éxito y error', async () => {
    const user = userEvent.setup()

    // Estado inicial: el aviso se muestra desde el primer render.
    const inicial = render(<App />)
    expect(screen.getByText(AVISO_MATERIAL_DIDACTICO)).toBeInTheDocument()
    inicial.unmount()

    // Estado cargando: la petición queda pendiente.
    let resolver: (valor: unknown) => void = () => {}
    fetchMock.mockImplementationOnce(
      () =>
        new Promise<unknown>((resolve) => {
          resolver = resolve
        }),
    )

    const consulta = render(<App />)
    await user.type(
      screen.getByLabelText('Tu pregunta'),
      '¿Qué necesito para el servicio social?',
    )
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Consultando documentos',
    )
    expect(screen.getByText(AVISO_MATERIAL_DIDACTICO)).toBeInTheDocument()

    // Estado éxito: el aviso sigue visible con la respuesta y fuentes.
    resolver(respuestaOk(RESPUESTA_EXITOSA))
    expect(await screen.findByText('Respuesta')).toBeInTheDocument()
    expect(screen.getByText(AVISO_MATERIAL_DIDACTICO)).toBeInTheDocument()
    consulta.unmount()

    // Estado error: la API responde 503.
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'sin corpus disponible' }),
    })

    render(<App />)
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
    expect(screen.getByText(AVISO_MATERIAL_DIDACTICO)).toBeInTheDocument()
  })
})
