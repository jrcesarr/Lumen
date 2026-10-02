"""Geracao de UUIDv7.

UUIDv7 comeca com o horario em milissegundos e termina com bits aleatorios:
- e ordenavel por data (bom para indices e paginacao);
- nao e sequencial, entao ninguem "chuta" o id de outro condominio na URL.
O Python 3.14 traz uuid.uuid7(); enquanto usamos 3.11, geramos aqui.
"""

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    ms = time.time_ns() // 1_000_000
    aleatorio = int.from_bytes(os.urandom(10), "big")
    valor = (ms & 0xFFFF_FFFF_FFFF) << 80  # 48 bits de tempo
    valor |= 0x7 << 76  # versao 7
    valor |= ((aleatorio >> 62) & 0xFFF) << 64  # 12 bits aleatorios
    valor |= 0b10 << 62  # variante RFC 4122
    valor |= aleatorio & ((1 << 62) - 1)  # 62 bits aleatorios
    return uuid.UUID(int=valor)
