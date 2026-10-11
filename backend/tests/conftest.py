"""Infra dos testes.

Igual a SmartFit: o banco de teste e criado do zero, as migrations rodam como admin
(num subprocesso, como em producao) e a API conecta como app_backend, o MESMO usuario
de producao. Se os testes usassem um superusuario, a RLS seria ignorada e os testes
de isolamento passariam por engano (ver test_guarda_conexao_respeita_rls).
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

# URL de um superusuario do Postgres local/CI. O banco "lumen_test" e criado a partir dela.
ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)
JWT_SECRET = "segredo-so-para-testes-com-pelo-menos-32-bytes"
SENHA_APP = "app_backend_teste"


def _trocar_banco(
    url: str, banco: str, usuario: str | None = None, senha: str | None = None
) -> str:
    partes = urlsplit(url)
    netloc = partes.netloc
    if usuario:
        host = netloc.rsplit("@", 1)[-1] if "@" in netloc else netloc
        netloc = f"{usuario}:{senha}@{host}"
    return urlunsplit((partes.scheme, netloc, f"/{banco}", partes.query, partes.fragment))


TEST_ADMIN_URL = _trocar_banco(ADMIN_URL, "lumen_test")
TEST_APP_URL = _trocar_banco(ADMIN_URL, "lumen_test", "app_backend", SENHA_APP)

# Precisa acontecer antes de qualquer import de app.* (get_settings e cacheado).
os.environ["DATABASE_URL"] = TEST_APP_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
os.environ["SUPABASE_JWT_SECRET"] = JWT_SECRET
os.environ["SUPABASE_URL"] = "http://supabase.teste"

TABELAS = [
    "outbox",
    "reservas",
    "vinculos",
    "areas_comuns",
    "unidades",
    "usuarios",
    "condominios",
    "auditoria",
]


@pytest.fixture(scope="session", autouse=True)
def banco_de_teste():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS lumen_test WITH (FORCE)")
        conn.execute("CREATE DATABASE lumen_test")

    env = {
        **os.environ,
        "MIGRATION_DATABASE_URL": TEST_ADMIN_URL.replace(
            "postgresql://", "postgresql+psycopg://", 1
        ),
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[1],
        env=env,
        check=True,
    )
    with psycopg.connect(TEST_ADMIN_URL, autocommit=True) as conn:
        # Role e global no cluster; a senha so existe no ambiente de teste.
        conn.execute(f"ALTER ROLE app_backend PASSWORD '{SENHA_APP}'")
    yield


@pytest.fixture
def admin():
    """Conexao de superusuario, so para preparar dados (ignora a RLS de proposito)."""
    with psycopg.connect(TEST_ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY CASCADE")
        yield conn


@pytest.fixture
async def engine():
    from app.shared.db import get_engine

    yield get_engine()
    await get_engine().dispose()


@pytest.fixture
async def client(engine):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste") as c:
        yield c
