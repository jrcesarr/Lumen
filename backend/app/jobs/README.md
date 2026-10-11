# Jobs

Tarefas em segundo plano. Hoje existe o worker da outbox (`python -m app.jobs.worker`, servico `worker` no compose): le os eventos pendentes, chama o handler de cada tipo (`handlers.py`) e tenta de novo com espera crescente se falhar, ate 5 vezes.

Garantia de entrega: pelo menos uma vez. Os handlers precisam ser idempotentes (use `evento.id`). O worker carimba a transacao com `papel = 'worker'`, que liga a policy `outbox_worker`; todo o resto continua com a RLS por condominio.

Lembretes agendados entram aqui quando forem implementados.
