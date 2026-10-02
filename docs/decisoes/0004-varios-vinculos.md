# 0004. Varios vinculos por pessoa e condominio ativo no header

**Contexto.** Na SmartFit cada usuario pertence a um unico contexto. Na Lumen, a mesma pessoa pode morar num condominio e ser sindica de outro.

**Decisao.** Tabela `vinculos (usuario, condominio, unidade, papel)`. O front envia o condominio ativo em `X-Condominio-Id`; a API confere que existe vinculo. Com um vinculo so, o header e opcional.

**Consequencias.** Papeis e permissoes mudam conforme o condominio ativo (testado em `test_papel_muda_conforme_condominio_ativo`). O front precisa limpar o cache ao trocar de condominio.
