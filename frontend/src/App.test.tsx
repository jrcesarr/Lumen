import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
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

afterEach(() => vi.restoreAllMocks())

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
})
