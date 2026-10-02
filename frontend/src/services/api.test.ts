import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: { getSession: async () => ({ data: { session: { access_token: 'tok-123' } } }) },
  },
}))

import { api, ApiError, setCondominioAtivo } from './api'

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

describe('api', () => {
  it('envia o token e o condominio ativo', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }))
    setCondominioAtivo('cond-a')

    await api('/unidades')

    const headers = fetchMock.mock.calls[0][1]!.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer tok-123')
    expect(headers.get('X-Condominio-Id')).toBe('cond-a')
  })

  it('transforma o envelope de erro em ApiError com request_id', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Sem permissao', request_id: 'req-9' }), { status: 403 }),
    )
    const erro = await api('/areas-comuns').catch((e) => e)
    expect(erro).toBeInstanceOf(ApiError)
    expect(erro).toMatchObject({ status: 403, requestId: 'req-9', message: 'Sem permissao' })
  })
})
