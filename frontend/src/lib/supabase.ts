import { createClient } from '@supabase/supabase-js'

// O front so usa o Supabase para LOGIN. Dados de negocio passam sempre pela nossa API.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL ?? 'http://localhost:54321',
  import.meta.env.VITE_SUPABASE_ANON_KEY ?? 'chave-anon-local',
)
