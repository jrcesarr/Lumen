import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../lib/supabase', () => ({
  supabase: { auth: { getSession: async () => ({ data: { session: null } }) } },
}))

import { SindicoHome } from './SindicoHome'

const PENDENTE = {
  id: 'r1', area_id: 'a1', unidade_id: 'u1', status: 'pendente', motivo_recusa: null,
  inicio: '2030-01-10T17:00:00Z', fim: '2030-01-10T21:00:00Z',
}

function responder(rotas: Record<string, { status: number; corpo: unknown }>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const caminho = String(url).replace(/^.*\/api\/v1/, '')
    const r = rotas[caminho] ?? { status: 200, corpo: [] }
    return new Response(JSON.stringify(r.corpo), { status: r.status })
  })
}

afterEach(() => vi.restoreAllMocks())

describe('SindicoHome', () => {
  it('mostra o pedido pendente e a mensagem do back quando o horario ja foi tomado', async () => {
    const fetchMock = responder({
      '/areas-comuns': { status: 200, corpo: [{ id: 'a1', nome: 'Churrasqueira' }] },
      '/reservas?status=pendente': { status: 200, corpo: [PENDENTE] },
      '/reservas/r1/aprovar': {
        status: 409,
        corpo: { detail: 'Ja existe uma reserva aprovada nesse horario', request_id: 'x' },
      },
    })
    render(
      <QueryClientProvider client={new QueryClient()}>
        <SindicoHome />
      </QueryClientProvider>,
    )

    expect(await screen.findByText(/Churrasqueira/)).toBeTruthy()
    fireEvent.click(screen.getByText('Aprovar'))
    expect((await screen.findByRole('alert')).textContent).toContain('Ja existe')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/reservas/r1/aprovar'),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
