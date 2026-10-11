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
      <div className="pagina-titulo">
        <h2>Minhas reservas</h2>
        <p>Peca areas comuns e acompanhe a resposta do sindico.</p>
      </div>
      {unidadeId && <NovaReserva areas={areas} unidadeId={unidadeId} />}
      <h3 className="secao-titulo">Pedidos</h3>
      {reservas.length === 0 && <p className="vazio">Voce ainda nao pediu nenhuma reserva.</p>}
      <ul>
        {reservas.map((r) => (
          <li key={r.id} className={`reserva reserva-${r.status}`}>
            <div className="reserva-info">
              <span className="reserva-area">{nomeDaArea(r.area_id)}</span>
              <span className="reserva-periodo">{periodo(r)}</span>
              {r.motivo_recusa && <span className="reserva-motivo">Motivo: {r.motivo_recusa}</span>}
            </div>
            <strong className={`status status-${r.status}`}>{r.status}</strong>
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
