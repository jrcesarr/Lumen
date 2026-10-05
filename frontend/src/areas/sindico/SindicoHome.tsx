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
      <h2>Reservas aguardando aprovacao</h2>
      {erro instanceof ApiError && <p role="alert">{erro.message}</p>}
      {pendentes.length === 0 && <p>Nenhum pedido pendente.</p>}
      <ul>
        {pendentes.map((r) => (
          <li key={r.id}>
            {nomeDaArea(r.area_id)}, {periodo(r)}
            <button onClick={() => aprovar.mutate(r.id)}>Aprovar</button>
            <button className="perigo" onClick={() => pedirRecusa(r.id)}>
              Recusar
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
