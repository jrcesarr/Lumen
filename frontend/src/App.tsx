import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { MoradorHome } from './areas/morador/MoradorHome'
import { PortariaHome } from './areas/portaria/PortariaHome'
import { SindicoHome } from './areas/sindico/SindicoHome'
import { SeletorCondominio } from './componentes/SeletorCondominio'
import { CondominioProvider, useCondominio } from './contexto/CondominioContext'
import { supabase } from './lib/supabase'
import { Login } from './paginas/Login'

/** Manda cada perfil para a sua area. Quem tem mais de um papel vai para o de maior acesso. */
function Inicio() {
  const { carregando, condominioId, papeis } = useCondominio()
  if (carregando) return <p>Carregando...</p>
  if (!condominioId) return <p>Escolha um condominio acima.</p>
  if (papeis.includes('sindico')) return <Navigate to="/sindico" replace />
  if (papeis.includes('porteiro')) return <Navigate to="/portaria" replace />
  return <Navigate to="/morador" replace />
}

function AreaLogada() {
  return (
    <CondominioProvider>
      <header>
        <SeletorCondominio />
      </header>
      <Routes>
        <Route path="/" element={<Inicio />} />
        <Route path="/morador/*" element={<MoradorHome />} />
        <Route path="/sindico/*" element={<SindicoHome />} />
        <Route path="/portaria/*" element={<PortariaHome />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </CondominioProvider>
  )
}

export default function App() {
  const [sessao, setSessao] = useState<Session | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSessao(data.session))
    const { data } = supabase.auth.onAuthStateChange((_evento, s) => setSessao(s))
    return () => data.subscription.unsubscribe()
  }, [])

  return <BrowserRouter>{sessao ? <AreaLogada /> : <Login />}</BrowserRouter>
}
