import { useQuery } from '@tanstack/react-query'
import { api, type AreaComum } from '../../services/api'

// A pagina de reservas entra aqui no proximo PR.
export function MoradorHome() {
  const { data: areas } = useQuery({ queryKey: ['areas'], queryFn: () => api<AreaComum[]>('/areas-comuns') })
  return (
    <section>
      <h2>Areas comuns</h2>
      <ul>{areas?.map((a) => <li key={a.id}>{a.nome}</li>)}</ul>
    </section>
  )
}
