# Rodando localmente e entrando na plataforma

O compose sobe banco, API e front, mas **nao** o login. O login e do Supabase, entao voce precisa de um projeto Supabase (o plano Free serve) e de dados de teste no banco local. Sao 5 passos.

> Os nomes de menu do painel do Supabase mudam de tempos em tempos. Se algum nao bater, procure pelo nome da tela.

## 1. Criar o projeto no Supabase
1. Em supabase.com, crie um projeto (regiao **Sao Paulo**). Guarde a senha do banco, mas ela nao sera usada aqui.
2. Em **Settings → API** copie a **Project URL** (`https://xxxx.supabase.co`) e a chave **anon / publishable**.

## 2. Criar dois usuarios de teste
Em **Authentication → Users → Add user → Create new user**, marque **Auto Confirm User** e crie:
- `sindico@teste.com` + uma senha
- `morador@teste.com` + uma senha

Copie o **UID** (um UUID) de cada um. Voce vai usar no passo 4.

## 3. Configurar os `.env`
Copie os exemplos e preencha:

`backend/.env`
```
DEBUG=true
SUPABASE_URL=https://xxxx.supabase.co
# SUPABASE_JWT_SECRET: deixe vazio. Projetos novos assinam o login com chave publica (JWKS),
# que a API busca na SUPABASE_URL. So preencha se o seu projeto ainda usar o segredo legado (HS256).
```

`frontend/.env`
```
VITE_API_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=<a chave anon do passo 1>
```
O `DATABASE_URL` do compose ja vem pronto no `docker-compose.yml`; nao precisa por no `.env`.

## 4. Criar os dados de teste no banco local
Com o compose rodando, abra o psql dentro do container:
```
docker compose exec db psql -U postgres -d lumen
```
Cole o SQL abaixo, **trocando os dois UUID** pelos UIDs do passo 2:

```sql
INSERT INTO usuarios (id, nome, email) VALUES
  ('UID-DO-SINDICO', 'Sergio Sindico', 'sindico@teste.com'),
  ('UID-DO-MORADOR', 'Ana Moradora',   'morador@teste.com');

INSERT INTO condominios (id, nome, cnpj) VALUES
  ('00000000-0000-7000-8000-000000000001', 'Residencial Aurora', '11111111000111');

INSERT INTO unidades (id, condominio_id, bloco, numero) VALUES
  ('00000000-0000-7000-8000-000000000101', '00000000-0000-7000-8000-000000000001', 'A', '101');

INSERT INTO areas_comuns (id, condominio_id, nome) VALUES
  ('00000000-0000-7000-8000-000000000201', '00000000-0000-7000-8000-000000000001', 'Churrasqueira');

INSERT INTO vinculos (id, usuario_id, condominio_id, unidade_id, papel) VALUES
  (gen_random_uuid(), 'UID-DO-SINDICO', '00000000-0000-7000-8000-000000000001', NULL, 'sindico'),
  (gen_random_uuid(), 'UID-DO-MORADOR', '00000000-0000-7000-8000-000000000001',
                      '00000000-0000-7000-8000-000000000101', 'morador');
```
Saia com `\q`.

Por que na mao: no Supabase de verdade, o perfil em `usuarios` nasce sozinho por trigger quando alguem se cadastra. No banco local nao existe o schema de login do Supabase, entao a gente cria o perfil e o vinculo (quem, em qual condominio, com qual papel).

## 5. Reiniciar e entrar
1. No terminal do compose: Ctrl+C e `docker compose up` de novo (o front le o `.env` ao iniciar).
2. Abra `http://localhost:5173`, entre com `morador@teste.com` e peca uma reserva da Churrasqueira (precisa ser com 24 h ou mais de antecedencia e no maximo 6 h de duracao).
3. Saia, entre com `sindico@teste.com` e aprove ou recuse o pedido.

## Se der erro
- **Login volta "token invalido":** confira se `SUPABASE_URL` do `backend/.env` e exatamente a Project URL, sem barra no fim, e reinicie a API.
- **Entra, mas a lista de condominios vem vazia:** o `UID` do SQL nao e o do usuario que logou.
- **Erro de CORS no navegador:** abra pelo endereco `localhost:5173` (nao pelo IP).
- Veja o log da API com `docker compose logs api`.
