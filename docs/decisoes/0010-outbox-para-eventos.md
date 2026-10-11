# 0010. Eventos pela outbox, entregues por um worker

**Contexto.** Aprovar uma reserva precisa avisar o morador. Mandar a notificacao dentro da requisicao tem dois furos: se o envio falha, a aprovacao ja foi gravada e o aviso se perde; se a API cai depois de enviar e antes de gravar, o morador recebe aviso de algo que nao aconteceu.

**Decisao.** A API grava o evento na tabela `outbox`, na mesma transacao da mudanca (`shared/outbox.publicar`). Um worker separado (`jobs/worker.py`) le os pendentes com `FOR UPDATE SKIP LOCKED`, chama o handler do tipo e marca `processado`. Se o handler falhar, o evento volta com espera crescente (30 s, 1 min, 2 min... teto de 1 h) e vira `falhou` na quinta tentativa. O worker nao tem condominio ativo, entao a transacao dele e carimbada com `papel = 'worker'`, que liga uma policy so da outbox; as demais tabelas continuam isoladas por condominio.

**Consequencias.** O evento existe se, e somente se, o fato existe. A entrega e pelo menos uma vez: os handlers precisam ser idempotentes. A ordem pode se perder entre tentativas de eventos diferentes. A tabela nao tem auditoria (cada tentativa seria uma linha). Hoje o handler so registra no log; o push do PWA e o WhatsApp entram como novos handlers, sem mudar a API. Eventos `falhou` precisam de um alerta quando houver monitoramento. Provado em `tests/test_outbox.py`.
