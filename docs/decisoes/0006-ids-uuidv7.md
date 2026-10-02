# 0006. IDs UUIDv7 gerados pela aplicacao

**Contexto.** IDs sequenciais expoem volume e sao adivinhaveis. UUIDv4 e aleatorio e fragmenta os indices.

**Decisao.** UUIDv7 (ordenado pelo tempo) gerado em Python (`app/shared/ids.py`), sem default no banco.

**Consequencias.** IDs seguros para URLs e bons para indice. A aplicacao conhece o id antes do insert, o que facilita eventos e auditoria.
