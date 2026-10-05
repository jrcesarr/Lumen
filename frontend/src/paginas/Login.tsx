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
        <h1>Lumen</h1>
        <input placeholder="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input placeholder="Senha" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} />
        <button type="submit">Entrar</button>
        {erro && <p role="alert">{erro}</p>}
      </form>
    </main>
  )
}
