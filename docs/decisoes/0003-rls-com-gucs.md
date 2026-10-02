# 0003. Isolamento entre condominios com RLS e GUCs

**Contexto.** Vazamento entre condominios e o pior bug possivel do produto. Filtro no codigo depende de ninguem esquecer.

**Decisao.** A API conecta como `app_backend` (sem BYPASSRLS). Cada transacao e carimbada com `app.condominio_id`; as policies comparam com esse valor. Sem carimbo, nenhuma linha. Mesmo modelo validado na SmartFit.

**Consequencias.** Isolamento garantido pelo banco e testado em `tests/test_rls.py`. Os testes precisam conectar como `app_backend`, e um teste-guarda falha se alguem trocar por superusuario.
