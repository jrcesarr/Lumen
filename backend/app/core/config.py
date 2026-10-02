"""Configuracao da aplicacao, lida das variaveis de ambiente (arquivo .env em dev)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    debug: bool = False

    # A API conecta SEMPRE como app_backend (sem BYPASSRLS). Ver docs/decisoes/0003.
    database_url: str = "postgresql+asyncpg://app_backend:app_backend@localhost:5432/lumen"
    # Migrations rodam com outro usuario, que pode criar tabelas.
    migration_database_url: str | None = None

    # Validacao do JWT do Supabase Auth.
    supabase_url: str = "http://localhost:54321"
    supabase_jwt_secret: str | None = None  # regime HS256 (legado e testes)
    jwt_audience: str = "authenticated"

    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
