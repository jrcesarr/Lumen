import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type AreaComum, type Reserva } from '../../services/api'

export const useAreas = () =>
  useQuery({ queryKey: ['areas'], queryFn: () => api<AreaComum[]>('/areas-comuns') })

export const useReservas = (status?: string) =>
  useQuery({
    queryKey: ['reservas', status],
    queryFn: () => api<Reserva[]>(`/reservas${status ? `?status=${status}` : ''}`),
  })

/** Toda acao invalida a lista: o que o usuario ve e sempre o estado do servidor. */
function useAcao<T>(fn: (dados: T) => Promise<unknown>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reservas'] }),
  })
}

export const useSolicitar = () =>
  useAcao((dados: { area_id: string; unidade_id: string; inicio: string; fim: string }) =>
    api<Reserva>('/reservas', { method: 'POST', body: JSON.stringify(dados) }),
  )
export const useAprovar = () =>
  useAcao((id: string) => api<Reserva>(`/reservas/${id}/aprovar`, { method: 'POST' }))
export const useRecusar = () =>
  useAcao(({ id, motivo }: { id: string; motivo: string }) =>
    api<Reserva>(`/reservas/${id}/recusar`, { method: 'POST', body: JSON.stringify({ motivo }) }),
  )
export const useCancelar = () =>
  useAcao((id: string) => api<Reserva>(`/reservas/${id}/cancelar`, { method: 'POST' }))

const formato = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
export const periodo = (r: Reserva) =>
  `${formato.format(new Date(r.inicio))} até ${formato.format(new Date(r.fim))}`
