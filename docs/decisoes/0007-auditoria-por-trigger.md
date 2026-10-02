# 0007. Auditoria por trigger no banco

**Contexto.** Sindicos precisam saber quem aprovou ou cancelou o que. Auditoria feita no codigo depende de lembrar de chamar.

**Decisao.** Trigger generica grava antes, depois, campos alterados, autor, papel e request_id em `auditoria`. A API so pode inserir e ler essa tabela.

**Consequencias.** Nenhuma escrita escapa, nem as feitas fora da API. O log e imutavel para a aplicacao (testado em `test_auditoria_e_imutavel_para_a_api`).
