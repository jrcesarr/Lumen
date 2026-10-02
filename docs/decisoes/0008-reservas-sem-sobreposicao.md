# 0008. Sobreposicao de reservas barrada no banco

**Contexto.** Dois sindicos (ou um sindico com duas abas) podem aprovar pedidos sobrepostos ao mesmo tempo. Uma checagem so no codigo ("existe aprovada nesse horario?") nao ve o que a outra transacao ainda nao confirmou.

**Decisao.** Exclusion constraint no Postgres: `EXCLUDE USING gist (area_id WITH =, tstzrange(inicio, fim, '[)') WITH &&) WHERE (status = 'aprovada')`. O service tambem checa antes, so para dar uma mensagem clara; se a corrida acontecer, o erro 23P01 do banco vira 409.

**Consequencias.** Impossivel ter duas aprovadas sobrepostas, mesmo com bug ou acesso direto ao banco. Pedidos pendentes podem se sobrepor (o sindico escolhe qual aprovar). O intervalo `[)` deixa 14h-18h e 18h-22h conviverem. Provado em `test_dois_sindicos_aprovando_ao_mesmo_tempo`.
