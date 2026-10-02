"""Conexao com o banco. A API usa o usuario app_backend, que NAO ignora a RLS."""

from collections.abc import AsyncGenerator
from datetime import datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    # Toda data do sistema e timestamptz (com fuso). Sem isso, o SQLAlchemy mapearia
    # datetime para "timestamp without time zone" e as comparacoes dariam erro.
    type_annotation_map = {datetime: DateTime(timezone=True)}


@lru_cache
def get_engine() -> AsyncEngine:
    # statement_cache_size=0: necessario com o pooler do Supabase em modo transaction.
    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_session)]
