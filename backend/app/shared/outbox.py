"""Outbox: a API grava o evento na MESMA transacao do fato e um worker entrega depois.

Se a API cair depois do commit, o evento continua na tabela e sai quando o worker
voltar. Se cair antes, nem o fato nem o evento existem. Nao ha meio-termo (ver
docs/decisoes/0010-outbox-para-eventos.md).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.context import RequestContext
from app.shared.db import Base
from app.shared.ids import uuid7


class Evento(Base):
    __tablename__ = "outbox"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    condominio_id: Mapped[UUID]
    tipo: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(default="pendente")
    tentativas: Mapped[int] = mapped_column(default=0)
    proxima_tentativa: Mapped[datetime] = mapped_column(server_default=func.now())
    ultimo_erro: Mapped[str | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    processado_em: Mapped[datetime | None]


def publicar(ctx: RequestContext, tipo: str, payload: dict[str, Any]) -> Evento:
    """Agenda um evento. Vai para o banco junto com o commit da requisicao."""
    evento = Evento(id=uuid7(), condominio_id=ctx.condominio_id, tipo=tipo, payload=payload)
    ctx.session.add(evento)
    return evento
