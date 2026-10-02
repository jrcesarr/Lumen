import { useCondominio } from '../contexto/CondominioContext'

export function SeletorCondominio() {
  const { me, condominioId, trocarCondominio } = useCondominio()
  const condominios = new Map(me?.vinculos.map((v) => [v.condominio_id, v.condominio_nome]))
  if (condominios.size <= 1) return null

  return (
    <select
      aria-label="Condominio"
      value={condominioId ?? ''}
      onChange={(e) => trocarCondominio(e.target.value)}
    >
      <option value="" disabled>
        Escolha o condominio
      </option>
      {[...condominios].map(([id, nome]) => (
        <option key={id} value={id}>
          {nome}
        </option>
      ))}
    </select>
  )
}
