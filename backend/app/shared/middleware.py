"""Gera o request_id de cada requisicao e registra uma linha de log por requisicao."""

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.requisicao")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        request.state.request_id = request_id
        inicio = time.perf_counter()
        response = await call_next(request)
        logger.info(
            "requisicao",
            extra={
                "request_id": request_id,
                "metodo": request.method,
                "caminho": request.url.path,
                "status": response.status_code,
                "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1),
            },
        )
        response.headers["X-Request-Id"] = request_id
        return response
