# Lumen

Plataforma de gestao de condominios: moradores, sindicos, portaria e o time de atendimento da Lumen num so lugar.

## Estrutura

```
backend/    API em FastAPI, um pacote por contexto (DDD)
  app/core/        configuracao, seguranca (JWT), catalogo de permissoes
  app/shared/      banco, contexto da requisicao (RLS), erros, middleware
  app/identidade/  usuarios e vinculos            (pronto)
  app/carteira/    condominios, unidades, areas   (pronto)
  app/reservas/    reservas de areas comuns       (proximo PR)
  app/chamados, portaria, comunicacao, financeiro, inteligencia, jobs
  alembic/         migrations em SQL explicito
frontend/   React + Vite + TypeScript, uma area por perfil
docs/       arquitetura e decisoes (ADRs)
```

## Rodando localmente

```bash
docker compose up            # banco, migrations, API (:8000), front (:5173) e MinIO
```

Sem Docker:

```bash
cd backend && cp .env.example .env && uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

cd frontend && cp .env.example .env && npm install && npm run dev
```

## Testes

```bash
cd backend && uv run pytest     # precisa de um Postgres; ver TEST_ADMIN_DATABASE_URL em tests/conftest.py
cd frontend && npm test
```

Os testes do back conectam como `app_backend`, o mesmo usuario de producao, para que a RLS seja testada de verdade.

## Leitura recomendada

1. [docs/arquitetura.md](docs/arquitetura.md): como uma requisicao atravessa o sistema.
2. [docs/decisoes/](docs/decisoes/): por que cada escolha foi feita.
