"""Erros de negocio e o envelope unico de erro: {"detail": ..., "request_id": ...}."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str = "Requisicao invalida") -> None:
        super().__init__(message)
        self.message = message


class NaoAutenticadoError(AppError):
    status_code = 401

    def __init__(self, message: str = "Nao autenticado") -> None:
        super().__init__(message)


class PermissaoNegadaError(AppError):
    status_code = 403

    def __init__(self, message: str = "Sem permissao para esta acao") -> None:
        super().__init__(message)


class NaoEncontradoError(AppError):
    status_code = 404

    def __init__(self, message: str = "Nao encontrado") -> None:
        super().__init__(message)


class ConflitoError(AppError):
    status_code = 409


class RegraDeNegocioError(AppError):
    """O pedido e valido no formato, mas quebra uma regra do negocio."""

    status_code = 422


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _resposta(request: Request, status: int, detail) -> JSONResponse:
    rid = _request_id(request)
    headers = {"X-Request-Id": rid} if rid else None
    return JSONResponse(
        status_code=status,
        content=jsonable_encoder({"detail": detail, "request_id": rid}),
        headers=headers,
    )


def registrar_handlers(app: FastAPI, debug: bool) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _resposta(request, exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError):
        return _resposta(request, 422, exc.errors())

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return _resposta(request, exc.status_code, exc.detail)

    @app.exception_handler(Exception)
    async def _nao_tratado(request: Request, exc: Exception):
        logger.exception("Erro nao tratado", extra={"request_id": _request_id(request)})
        return _resposta(request, 500, str(exc) if debug else "Erro interno")
