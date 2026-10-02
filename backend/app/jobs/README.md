# Jobs

Tarefas em segundo plano (lembretes, envio da outbox). Usam montar_contexto(), o mesmo carimbo da API, entao a RLS vale aqui tambem.

Estrutura quando for implementado: `models.py` (tabelas), `schemas.py` (contratos da API), `domain.py` (regras puras, sem banco), `service.py` (casos de uso), `router.py` (endpoints).
