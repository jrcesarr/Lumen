import { useState, type FormEvent } from 'react'
import { supabase } from '../lib/supabase'

export function Login() {
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  async function entrar(e: FormEvent) {
    e.preventDefault()
    const { error } = await supabase.auth.signInWithPassword({ email, password: senha })
    setErro(error ? 'E-mail ou senha invalidos' : null)
  }

  return (
    <main className="login">
      <form onSubmit={entrar}>
        <div className="login-cabecalho">
          <span className="marca-icone" aria-hidden="true">L</span>
          <h1>Lumen</h1>
          <p>Administradora de Condominios</p>
        </div>
        <label className="campo">
          <span>E-mail</span>
          <input placeholder="voce@exemplo.com" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="campo">
          <span>Senha</span>
          <input placeholder="Sua senha" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} />
        </label>
        <button type="submit">Entrar</button>
        {erro && <p role="alert">{erro}</p>}
      </form>
    </main>
  )
}
