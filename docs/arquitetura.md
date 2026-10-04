# Arquitetura

![Diagrama da arquitetura](diagramas/arquitetura.svg)

## Onde cada parte roda

| Parte | Onde | Por quê |
|---|---|---|
| Front (React PWA) | Servido pelo nginx da VM | Build estático; um servidor a menos |
| API FastAPI e worker | VM Linux na Oracle Cloud, região São Paulo, com Docker Compose | Mesmo modelo de infra da SmartFit; um deploy só |
| MinIO (arquivos) | Mesma VM | Fotos, NFs e regimentos; acesso por link assinado |
| PostgreSQL e Auth | Supabase, região São Paulo, plano pago | Dados no Brasil (LGPD), backup gerenciado, login pronto |
| WhatsApp, Asaas, LLM | SaaS externos | Chamados só pela API ou pelo worker, nunca pelo front |

O fluxo de cada funcionalidade (telas e endpoints) está em [fluxos-de-dados.md](fluxos-de-dados.md).

## Uma requisicao, do clique ao banco

1. O front faz login no **Supabase Auth** e recebe um JWT.
2. Toda chamada passa por `services/api.ts`, que envia o token e o header `X-Condominio-Id` (condominio ativo).
3. A API valida o JWT (`core/security.py`) e monta o **RequestContext** (`shared/context.py`):
   le os vinculos do usuario, confere que ele pertence ao condominio pedido e calcula papeis e permissoes.
4. O contexto **carimba a transacao** com `set_config('app.condominio_id', ..., true)` e similares.
5. As policies de **RLS** no Postgres so mostram linhas desse condominio. Sem carimbo, nenhuma linha (falha fechada).
6. Triggers gravam a **auditoria** (quem, quando, o que mudou, request_id) em toda escrita.

## Tres camadas de protecao

| Camada | Onde | Protege contra |
|---|---|---|
| Permissao (`RequirePermission`) | API | morador tentando aprovar reserva |
| RLS por condominio | Postgres | qualquer bug que esqueca o filtro de condominio |
| FKs compostas `(id, condominio_id)` | Postgres | dado de um condominio apontando para outro |

## Contexto por pasta

Cada contexto tem `models.py` (tabelas), `schemas.py` (contratos), `domain.py` (regras puras, testaveis sem banco),
`service.py` (casos de uso) e `router.py` (endpoints). Um contexto nao importa o `service` de outro sem necessidade;
quando precisar reagir a algo, usa eventos via tabela outbox (a partir de Comunicacao).

## Tabela nova, protegida em uma linha

```sql
SELECT app_preparar_tabela('reservas');  -- grants + RLS + auditoria + atualizado_em
```
