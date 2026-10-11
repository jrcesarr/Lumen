import { useEffect, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { useQueryClient } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { MoradorHome } from './areas/morador/MoradorHome'
import { PortariaHome } from './areas/portaria/PortariaHome'
import { SindicoHome } from './areas/sindico/SindicoHome'
import { SeletorCondominio } from './componentes/SeletorCondominio'
import { CondominioProvider, useCondominio } from './contexto/CondominioContext'
import { supabase } from './lib/supabase'
import { Login } from './paginas/Login'
import type { Vinculo } from './services/api'

/** Manda cada perfil para a sua area. Quem tem mais de um papel vai para o de maior acesso. */
function Inicio() {
  const { me, carregando, condominioId, papeis } = useCondominio()
  if (carregando) return <p>Carregando...</p>
  if (!me) return <p>Nao foi possivel carregar seus dados. Tente entrar de novo.</p>
  if (me.vinculos.length === 0) {
    return <p>Sua conta ainda nao esta vinculada a um condominio. Peca ao sindico para liberar seu acesso.</p>
  }
  if (!condominioId) return <p>Escolha um condominio acima.</p>
  if (papeis.includes('sindico')) return <Navigate to="/sindico" replace />
  if (papeis.includes('porteiro')) return <Navigate to="/portaria" replace />
  if (papeis.includes('morador')) return <Navigate to="/morador" replace />
  return <p>Seu perfil ainda nao tem uma area no app.</p>
}

/** A URL nao da acesso: quem nao tem o papel da area volta para o inicio. */
function SoPara({ papel, children }: { papel: Vinculo['papel']; children: ReactNode }) {
  const { carregando, papeis } = useCondominio()
  if (carregando) return <p>Carregando...</p>
  return papeis.includes(papel) ? children : <Navigate to="/" replace />
}

function AreaLogada({ email }: { email?: string }) {
  return (
    <CondominioProvider>
      <header className="topo">
        <div className="topo-conteudo">
          <span className="marca">
            <span className="marca-icone" aria-hidden="true">L</span>
            Lumen
          </span>
          <SeletorCondominio />
          {email && (
            <span className="usuario">
              <span className="avatar" aria-hidden="true">{email[0]}</span>
              <span className="usuario-email">{email}</span>
            </span>
          )}
          <button type="button" className="secundario" onClick={() => supabase.auth.signOut()}>
            Sair
          </button>
        </div>
      </header>
      <main className="conteudo">
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/morador/*" element={<SoPara papel="morador"><MoradorHome /></SoPara>} />
          <Route path="/sindico/*" element={<SoPara papel="sindico"><SindicoHome /></SoPara>} />
          <Route path="/portaria/*" element={<SoPara papel="porteiro"><PortariaHome /></SoPara>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </CondominioProvider>
  )
}

export default function App() {
  const queryClient = useQueryClient()
  const [sessao, setSessao] = useState<Session | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSessao(data.session))
    const { data } = supabase.auth.onAuthStateChange((evento, s) => {
      // O cache e do usuario que saiu; o proximo login nao pode ver os dados dele.
      if (evento === 'SIGNED_OUT') queryClient.clear()
      setSessao(s)
    })
    return () => data.subscription.unsubscribe()
  }, [queryClient])

  return (
    <BrowserRouter>
      {sessao ? (
        <AreaLogada email={sessao.user.email} />
      ) : (
        // Sem sessao, qualquer URL volta para a raiz: quem entrar depois e mandado para a propria area.
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      )}
    </BrowserRouter>
  )
}
