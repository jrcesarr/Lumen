import { useCondominio } from '../../contexto/CondominioContext'
import { NovaReserva } from '../reservas/NovaReserva'
import { periodo, useAreas, useCancelar, useReservas } from '../reservas/reservasApi'

export function MoradorHome() {
  const { me, condominioId } = useCondominio()
  const { data: areas = [] } = useAreas()
  const { data: reservas = [] } = useReservas()
  const cancelar = useCancelar()
  const unidadeId = me?.vinculos.find(
    (v) => v.condominio_id === condominioId && v.unidade_id,
  )?.unidade_id
  const nomeDaArea = (id: string) => areas.find((a) => a.id === id)?.nome ?? 'Area'

  return (
    <section>
      <h2>Minhas reservas</h2>
      {unidadeId && <NovaReserva areas={areas} unidadeId={unidadeId} />}
      <ul>
        {reservas.map((r) => (
          <li key={r.id}>
            {nomeDaArea(r.area_id)}, {periodo(r)}: <strong className={`status status-${r.status}`}>{r.status}</strong>
            {r.motivo_recusa && <> ({r.motivo_recusa})</>}
            {(r.status === 'pendente' || r.status === 'aprovada') && (
              <button className="perigo" onClick={() => cancelar.mutate(r.id)}>
                Cancelar
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
