import { useState, type FormEvent } from 'react'
import { ApiError, type AreaComum } from '../../services/api'
import { useSolicitar } from './reservasApi'

type Props = { areas: AreaComum[]; unidadeId: string }

export function NovaReserva({ areas, unidadeId }: Props) {
  const [areaId, setAreaId] = useState('')
  const [inicio, setInicio] = useState('')
  const [fim, setFim] = useState('')
  const solicitar = useSolicitar()

  function enviar(e: FormEvent) {
    e.preventDefault()
    // <input type="datetime-local"> nao tem fuso; new Date() usa o fuso do navegador
    // e toISOString() manda em UTC. A API recusa horario sem fuso.
    solicitar.mutate({
      area_id: areaId,
      unidade_id: unidadeId,
      inicio: new Date(inicio).toISOString(),
      fim: new Date(fim).toISOString(),
    })
  }

  return (
    <form onSubmit={enviar}>
      <h3>Nova reserva</h3>
      <select aria-label="Area" value={areaId} onChange={(e) => setAreaId(e.target.value)} required>
        <option value="">Escolha a area</option>
        {areas.map((a) => (
          <option key={a.id} value={a.id}>
            {a.nome}
          </option>
        ))}
      </select>
      <input aria-label="Inicio" type="datetime-local" value={inicio} onChange={(e) => setInicio(e.target.value)} required />
      <input aria-label="Fim" type="datetime-local" value={fim} onChange={(e) => setFim(e.target.value)} required />
      <button type="submit" disabled={solicitar.isPending}>
        Pedir reserva
      </button>
      {solicitar.isSuccess && <p>Pedido enviado.</p>}
      {solicitar.error instanceof ApiError && <p role="alert">{solicitar.error.message}</p>}
    </form>
  )
}
