"""Ponto de entrada da API. Cada contexto (DDD) registra o proprio router aqui."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.carteira.router import router as carteira_router
from app.core.config import get_settings
from app.core.logging import configurar_logging
from app.identidade.router import router as identidade_router
from app.shared.errors import registrar_handlers
from app.shared.middleware import RequestIdMiddleware

API_V1 = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    configurar_logging(settings.debug)

    app = FastAPI(title="Lumen API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )
    app.add_middleware(RequestIdMiddleware)
    registrar_handlers(app, settings.debug)

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(identidade_router, prefix=API_V1)
    app.include_router(carteira_router, prefix=API_V1)
    return app


app = create_app()
