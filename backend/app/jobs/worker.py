"""Worker da outbox: python -m app.jobs.worker"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import configurar_logging
from app.jobs.handlers import HANDLERS
from app.jobs.outbox import processar_lote
from app.shared.db import get_engine

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 5


async def main() -> None:
    configurar_logging(get_settings().debug)
    logger.info("Worker da outbox iniciado")
    while True:
        try:
            async with AsyncSession(get_engine()) as session:
                pegou = await processar_lote(session, HANDLERS)
        except Exception:  # noqa: BLE001 - banco fora do ar nao pode derrubar o worker
            logger.exception("Falha ao processar a outbox")
            pegou = 0
        if pegou == 0:
            await asyncio.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    asyncio.run(main())
