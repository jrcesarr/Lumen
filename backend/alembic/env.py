"""Alembic roda as migrations com MIGRATION_DATABASE_URL (usuario que pode criar tabelas).

As migrations sao SQL explicito (op.execute), e nao autogeradas: assim cada policy de
RLS, trigger e grant fica visivel e revisavel no PR.
"""

from sqlalchemy import create_engine

from alembic import context
from app.core.config import get_settings


def _url() -> str:
    settings = get_settings()
    url = settings.migration_database_url or settings.database_url
    # Migrations usam driver sincrono (psycopg); a API usa asyncpg.
    return url.replace("+asyncpg", "+psycopg")


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
