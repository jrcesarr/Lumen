import { ApiError } from '../../services/api'
import { periodo, useAprovar, useAreas, useRecusar, useReservas } from '../reservas/reservasApi'

export function SindicoHome() {
  const { data: areas = [] } = useAreas()
  const { data: pendentes = [] } = useReservas('pendente')
  const aprovar = useAprovar()
  const recusar = useRecusar()
  const erro = aprovar.error ?? recusar.error
  const nomeDaArea = (id: string) => areas.find((a) => a.id === id)?.nome ?? 'Area'

  function pedirRecusa(id: string) {
    const motivo = window.prompt('Motivo da recusa')
    if (motivo?.trim()) recusar.mutate({ id, motivo })
  }

  return (
    <section>
      <div className="pagina-titulo">
        <h2>Reservas aguardando aprovacao</h2>
        <p>Aprove ou recuse os pedidos dos moradores.</p>
      </div>
      {erro instanceof ApiError && <p role="alert">{erro.message}</p>}
      {pendentes.length === 0 && <p className="vazio">Nenhum pedido pendente.</p>}
      <ul>
        {pendentes.map((r) => (
          <li key={r.id} className="reserva reserva-pendente">
            <div className="reserva-info">
              <span className="reserva-area">{nomeDaArea(r.area_id)}</span>
              <span className="reserva-periodo">{periodo(r)}</span>
            </div>
            <div className="reserva-acoes">
              <button className="perigo" onClick={() => pedirRecusa(r.id)}>
                Recusar
              </button>
              <button onClick={() => aprovar.mutate(r.id)}>Aprovar</button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
