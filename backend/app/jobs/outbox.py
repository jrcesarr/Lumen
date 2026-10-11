"""Entrega dos eventos da outbox. Um lote por chamada; quem repete e o worker.

Garantia: pelo menos uma vez (at-least-once). Se o processo cair depois de o handler
agir e antes do commit, o evento volta e o handler roda de novo. Por isso os handlers
precisam ser idempotentes (use evento.id como chave de deduplicacao).
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.context import carimbar
from app.shared.outbox import Evento

logger = logging.getLogger(__name__)

Handler = Callable[[Evento], Awaitable[None]]

MAX_TENTATIVAS = 5
ESPERA_BASE_SEGUNDOS = 30
ESPERA_MAX_SEGUNDOS = 3600


def espera_apos_falha(tentativas: int) -> timedelta:
    """Backoff exponencial: 1, 2, 4... vezes a base, com teto de 1 hora."""
    segundos = min(ESPERA_BASE_SEGUNDOS * 2 ** (tentativas - 1), ESPERA_MAX_SEGUNDOS)
    return timedelta(seconds=segundos)


async def processar_lote(
    session: AsyncSession,
    handlers: dict[str, Handler],
    *,
    agora: datetime | None = None,
    limite: int = 20,
) -> int:
    """Entrega os eventos vencidos e devolve quantos pegou (para o worker saber se dorme)."""
    agora = agora or datetime.now(UTC)
    async with session.begin():
        # O worker varre todos os condominios: o papel 'worker' habilita a policy
        # outbox_worker (migration 004), que existe so nesta tabela.
        await carimbar(session, papel="worker", request_id="worker-outbox")
        eventos = (
            await session.scalars(
                select(Evento)
                .where(Evento.status == "pendente", Evento.proxima_tentativa <= agora)
                .order_by(Evento.criado_em)
                .limit(limite)
                # Dois workers nao pegam o mesmo evento: quem chegou depois pula o travado.
                .with_for_update(skip_locked=True)
            )
        ).all()

        for evento in eventos:
            try:
                handler = handlers.get(evento.tipo)
                if handler is None:
                    raise LookupError(f"sem handler para {evento.tipo}")
                async with session.begin_nested():
                    await handler(evento)
            except Exception as erro:  # noqa: BLE001 - qualquer falha vira nova tentativa
                evento.tentativas += 1
                evento.ultimo_erro = str(erro)[:500]
                if evento.tentativas >= MAX_TENTATIVAS:
                    evento.status = "falhou"
                else:
                    evento.proxima_tentativa = agora + espera_apos_falha(evento.tentativas)
                logger.warning(
                    "Evento falhou",
                    extra={"evento": str(evento.id), "tentativas": evento.tentativas},
                )
            else:
                evento.status = "processado"
                evento.processado_em = agora
        return len(eventos)
