# Arquitetura

![Diagrama da arquitetura](diagramas/arquitetura.svg)

## Onde cada parte roda

| Parte | Onde | Por quê |
|---|---|---|
| Front (React PWA) | Servido pelo nginx da VM | Build estático; um servidor a menos |
| API FastAPI e worker | VM Oracle Always Free, região São Paulo, conta Pay As You Go, Docker Compose | Custo zero sem o desligamento por ociosidade da conta só gratuita; mesmo modelo da SmartFit |
| Oracle Object Storage (arquivos e backups) | Oracle Cloud, fora da VM, regiao Sao Paulo | Fotos, NFs e regimentos em `lumen-arquivos` (versionado); dumps em `lumen-backup`. API S3, acesso por link assinado ([ADR 0011](decisoes/0011-object-storage-da-oracle.md)) |
| PostgreSQL e Auth | Supabase Free, região São Paulo | Dados no Brasil (LGPD) e login pronto. Sem backup no Free: `pg_dump` diário no Object Storage da Oracle ([backup.md](backup.md)). Pro (US$ 25/mês) ao passar de 400 MB ou na fase 2 |
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
quando precisar reagir a algo, usa eventos via tabela outbox: `shared/outbox.py` grava o evento na mesma transacao
do fato e o worker (`jobs/`) entrega depois, com retry ([ADR 0010](decisoes/0010-outbox-para-eventos.md)).
Hoje as Reservas publicam `reserva.solicitada`, `reserva.aprovada`, `reserva.recusada` e `reserva.cancelada`; os handlers so registram no log
ate o contexto Comunicacao enviar push e WhatsApp.

## Tabela nova, protegida em uma linha

```sql
SELECT app_preparar_tabela('reservas');  -- grants + RLS + auditoria + atualizado_em
```
