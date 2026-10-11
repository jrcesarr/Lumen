import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { signOut, getSession } = vi.hoisted(() => ({ signOut: vi.fn(), getSession: vi.fn() }))

vi.mock('./lib/supabase', () => ({
  supabase: {
    auth: {
      getSession,
      signOut,
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
    },
  },
}))

import App from './App'

function renderizar() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('App', () => {
  it('mostra o login quando nao ha sessao', async () => {
    getSession.mockResolvedValue({ data: { session: null } })
    renderizar()
    expect(await screen.findByRole('button', { name: 'Entrar' })).toBeTruthy()
  })

  it('mostra o e-mail e permite sair quando ha sessao', async () => {
    getSession.mockResolvedValue({
      data: { session: { access_token: 't', user: { email: 'ana@teste.com' } } },
    })
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      async () =>
        new Response(JSON.stringify({ id: 'u1', nome: 'Ana', email: 'ana@teste.com', vinculos: [] })),
    )
    renderizar()

    expect(await screen.findByText('ana@teste.com')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(signOut).toHaveBeenCalledOnce()
  })

  it('manda o sindico para a area dele mesmo se a URL for de morador', async () => {
    window.history.pushState({}, '', '/morador')
    getSession.mockResolvedValue({
      data: { session: { access_token: 't', user: { email: 'sindico@teste.com' } } },
    })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) =>
      String(url).endsWith('/me')
        ? new Response(
            JSON.stringify({
              id: 'u1',
              nome: 'Sindico',
              email: 'sindico@teste.com',
              vinculos: [{ condominio_id: 'c1', condominio_nome: 'C1', papel: 'sindico', unidade_id: null }],
            }),
          )
        : new Response('[]'),
    )
    renderizar()

    expect(await screen.findByText('Reservas aguardando aprovacao')).toBeTruthy()
    expect(window.location.pathname).toBe('/sindico')
  })

  it('volta para a raiz quando nao ha sessao', async () => {
    window.history.pushState({}, '', '/sindico')
    getSession.mockResolvedValue({ data: { session: null } })
    renderizar()

    expect(await screen.findByRole('button', { name: 'Entrar' })).toBeTruthy()
    expect(window.location.pathname).toBe('/')
  })
})
