"""O que fazer com cada evento. Hoje so registra no log.

Quando Comunicacao existir, estes handlers passam a mandar push do PWA (e, na fase 2,
WhatsApp). O contrato nao muda: recebe o evento e levanta excecao se nao conseguir.
"""

import logging

from app.jobs.outbox import Handler
from app.shared.outbox import Evento

logger = logging.getLogger(__name__)


async def registrar_no_log(evento: Evento) -> None:
    logger.info("Notificar", extra={"evento": str(evento.id), "tipo": evento.tipo})


HANDLERS: dict[str, Handler] = {
    "reserva.solicitada": registrar_no_log,  # avisar o sindico
    "reserva.aprovada": registrar_no_log,  # avisar o morador
    "reserva.recusada": registrar_no_log,  # avisar o morador, com o motivo
    "reserva.cancelada": registrar_no_log,  # avisar a outra parte (sindico ou morador)
}
