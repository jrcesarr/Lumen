# Seguranca e LGPD

Lista de ameacas, a defesa de cada uma e o status. **Feito** = existe no codigo e tem teste. **Pendente** = identificado, ainda sem implementacao.

## Como as camadas se encaixam

Uma requisicao passa por quatro barreiras, e cada uma cobre o furo da anterior:

1. **JWT** (`core/security.py`): so entra quem tem um token valido do Supabase Auth.
2. **Vinculo e permissao** (`shared/context.py`): a API confere que a pessoa pertence ao condominio pedido e se o papel dela tem a permissao `recurso.acao` do endpoint.
3. **RLS no Postgres**: mesmo que o codigo esqueca um filtro, o banco so devolve linhas do condominio ativo. A API conecta como `app_backend`, que nao pode ignorar a RLS.
4. **FKs compostas** `(id, condominio_id)`: um registro de um condominio nao consegue apontar para unidade ou area de outro.

Por tras de tudo, um trigger grava a **auditoria** de toda escrita.

## Ameacas e defesas

| Ameaca | Defesa | Status |
|---|---|---|
| Condominio A le ou grava dados do B | RLS por condominio + FKs compostas; `tests/test_rls.py` | Feito |
| Bug que esquece o filtro de condominio | RLS falha fechada: sem carimbo, zero linhas | Feito |
| Alguem troca a conexao por um superusuario e a RLS some | `app_backend` e NOBYPASSRLS; teste-guarda `test_guarda_conexao_respeita_rls` | Feito |
| Morador usa funcao de sindico | `RequirePermission` em cada endpoint; catalogo `recurso.acao` | Feito |
| Usuario envia `X-Condominio-Id` de outro predio | O vinculo e conferido antes de carimbar | Feito |
| Token falso, expirado, de outro projeto ou sem `exp`/`sub` | Assinatura, `aud`, `iss` e `exp`/`sub` obrigatorios; lista fechada de algoritmos | Feito |
| Tabelas acessiveis pela API automatica do Supabase (PostgREST) | `app_preparar_tabela` faz `REVOKE` para `anon`, `authenticated` e `service_role`. `usuarios` e `auditoria` ficam protegidas pela RLS, mas `papeis` e `papel_permissoes` (so o catalogo de papeis) ainda nao tem o `REVOKE` | Parcial |
| Morador le e-mail e telefone dos vizinhos | A policy de `usuarios` so mostra o proprio usuario e, para sindico, atendente e admin, os do condominio ativo; `test_morador_nao_le_dados_dos_vizinhos` | Feito |
| Alteracao sem rastro | Auditoria por trigger, imutavel para a API | Feito |
| Duas aprovacoes sobrepostas (corrida) | Exclusion constraint no banco | Feito |
| Aviso perdido se a API cair | Outbox na mesma transacao + worker com retry | Feito |
| Perda de dados | `pg_dump` diario com restore testado no CI | Feito (restore com dump real do Supabase: pendente) |
| Chave secreta do Supabase no front ou no repo | So a chave publicavel vai ao front; o repo tem apenas `.env.example` | Feito (sem varredura automatica de segredos) |
| Front mostra tela que a pessoa nao deveria ver | A guarda de rotas e so de experiencia; a autorizacao esta na API | Feito |
| Hash de senha no backup (schema `auth`) | Criptografar o dump antes de subir ao bucket e restringir o acesso | Pendente |
| Forca bruta e excesso de requisicoes | Login: limite do Supabase Auth. API: limite no nginx (abaixo) | Pendente |
| Dependencia com vulnerabilidade conhecida | `pip-audit`, `npm audit` ou Dependabot no CI | Pendente |
| Dado pessoal enviado ao LLM | O assistente (Claude Haiku) recebe so pergunta e regimento; o payload da outbox leva ids, sem nome ou telefone | Parcial (LLM ainda nao integrado) |
| Webhook de pagamento forjado ou repetido | Validar assinatura e processar de forma idempotente | Futuro (Financeiro) |
| Upload malicioso | Link assinado com expiracao, tipo e tamanho validados | Futuro (Chamados) |

## Limites conhecidos

- **A RLS confia na aplicacao.** Quem carimba a transacao e o proprio `app_backend`, entao ela protege contra um filtro esquecido, nao contra codigo comprometido rodando como `app_backend`. O papel `worker` da outbox e um exemplo: so vale na tabela `outbox`, mas e carimbado pelo codigo.
- **Auditoria imutavel, nao infalivel.** A API nao apaga nem altera o log, mas pode inserir linhas com `origem = 'app'` para qualquer condominio.
- **O worker segura a transacao durante a entrega.** Com handlers lentos (WhatsApp) sera preciso entregar fora da transacao.
- **Visao consolidada da Lumen:** admin e atendente tem um vinculo por condominio; relatorios da carteira inteira exigem uma decisao propria.

## Limite de requisicoes no nginx (planejado)

O nginx da VM recebe tudo antes da API. Com `limit_req`, ele recusa com 429 quem passa de um ritmo, sem a API gastar CPU. Exemplo:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
  location /api/ {
    limit_req zone=api burst=20 nodelay;
    limit_req_status 429;
    proxy_pass http://api:8000;
  }
}
```

- `rate=10r/s` e a media permitida por IP, e `burst=20` deixa passar picos curtos (o front dispara varias chamadas ao abrir uma tela).
- Cuidado: moradores do mesmo predio costumam sair pelo mesmo IP (o wifi do condominio). Um limite apertado por IP bloquearia o predio inteiro, entao o numero precisa ser folgado.
- Esse arquivo ainda nao esta no repo, porque o `infra/` de producao nao foi feito.

## LGPD

- **Papeis:** a Lumen e controladora, a plataforma e operadora e o provedor de LLM e suboperador.
- **Minimizacao:** o assistente do regimento nao recebe nome, CPF nem unidade.
- **Transferencia internacional (art. 33):** exige clausulas contratuais padrao quando o LLM processa fora do Brasil.
- **Trilha:** a tabela `auditoria` mostra quem alterou o que e quando, o que apoia o atendimento a pedidos de titulares.
- **Retencao e exclusao:** ainda nao definidas; dependem do contrato com a Lumen.
