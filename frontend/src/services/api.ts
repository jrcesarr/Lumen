import { supabase } from '../lib/supabase'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
const CHAVE_CONDOMINIO = 'lumen.condominioAtivo'

export function getCondominioAtivo(): string | null {
  return localStorage.getItem(CHAVE_CONDOMINIO)
}

export function setCondominioAtivo(id: string) {
  localStorage.setItem(CHAVE_CONDOMINIO, id)
}

export class ApiError extends Error {
  status: number
  requestId: string | null

  constructor(status: number, detail: string, requestId: string | null) {
    super(detail)
    this.status = status
    this.requestId = requestId
  }
}

/** Unico ponto de saida para a API: anexa o token e o condominio ativo em toda chamada. */
export async function api<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (data.session) headers.set('Authorization', `Bearer ${data.session.access_token}`)
  const condominio = getCondominioAtivo()
  if (condominio) headers.set('X-Condominio-Id', condominio)

  const resposta = await fetch(`${BASE}${caminho}`, { ...init, headers })
  if (!resposta.ok) {
    // Envelope padrao do back: { detail, request_id }. O request_id ajuda no suporte.
    const corpo = await resposta.json().catch(() => ({}))
    throw new ApiError(resposta.status, corpo.detail ?? 'Erro inesperado', corpo.request_id ?? null)
  }
  return resposta.status === 204 ? (undefined as T) : resposta.json()
}

export type Vinculo = {
  condominio_id: string
  condominio_nome: string
  papel: 'morador' | 'sindico' | 'porteiro' | 'prestador' | 'atendente' | 'admin'
  unidade_id: string | null
}
export type Me = { id: string; nome: string; email: string; vinculos: Vinculo[] }
export type AreaComum = { id: string; nome: string; capacidade: number | null; exige_aprovacao: boolean }

export type StatusReserva = 'pendente' | 'aprovada' | 'recusada' | 'cancelada'
export type Reserva = {
  id: string
  area_id: string
  unidade_id: string
  inicio: string
  fim: string
  status: StatusReserva
  motivo_recusa: string | null
}
