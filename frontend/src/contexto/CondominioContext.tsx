import { createContext, useContext, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getCondominioAtivo, setCondominioAtivo, type Me, type Vinculo } from '../services/api'

type Valor = {
  me: Me | undefined
  carregando: boolean
  condominioId: string | null
  papeis: Vinculo['papel'][]
  trocarCondominio: (id: string) => void
}

const Ctx = createContext<Valor | null>(null)

/** Diferente da SmartFit: a mesma pessoa pode ter vinculos em varios condominios. */
export function CondominioProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { data: me, isLoading } = useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me') })
  const [escolhido, setEscolhido] = useState(getCondominioAtivo())

  const condominios = new Set(me?.vinculos.map((v) => v.condominio_id))
  // Se so ha um condominio, ele e o ativo; se o salvo nao vale mais, nenhum.
  const condominioId =
    escolhido && condominios.has(escolhido)
      ? escolhido
      : condominios.size === 1
        ? [...condominios][0]
        : null
  const papeis = me?.vinculos.filter((v) => v.condominio_id === condominioId).map((v) => v.papel) ?? []

  function trocarCondominio(id: string) {
    setCondominioAtivo(id)
    setEscolhido(id)
    // Os dados em cache eram do condominio anterior: descarta tudo menos o /me.
    queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
  }

  return (
    <Ctx.Provider value={{ me, carregando: isLoading, condominioId, papeis, trocarCondominio }}>
      {children}
    </Ctx.Provider>
  )
}

export function useCondominio() {
  const valor = useContext(Ctx)
  if (!valor) throw new Error('useCondominio fora do CondominioProvider')
  return valor
}
