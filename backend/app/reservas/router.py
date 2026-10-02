from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.permissions import Permissao
from app.reservas import service
from app.reservas.domain import Status
from app.reservas.schemas import RecusaIn, ReservaIn, ReservaOut
from app.shared.context import RequestContext, RequestContextDep, RequirePermission

router = APIRouter(prefix="/reservas", tags=["reservas"])


def _com(permissao: Permissao):
    return Annotated[RequestContext, Depends(RequirePermission(permissao))]


@router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
async def solicitar(dados: ReservaIn, ctx: _com(Permissao.RESERVA_SOLICITAR)):
    return await service.solicitar(ctx, dados)


@router.get("", response_model=list[ReservaOut])
async def listar(
    ctx: RequestContextDep,
    de: datetime | None = None,
    ate: datetime | None = None,
    status: Status | None = None,
):
    """Sindico ve todas do condominio; morador, so as da propria unidade."""
    return await service.listar(ctx, de=de, ate=ate, status=status)


@router.post("/{reserva_id}/aprovar", response_model=ReservaOut)
async def aprovar(reserva_id: UUID, ctx: _com(Permissao.RESERVA_APROVAR)):
    return await service.aprovar(ctx, reserva_id)


@router.post("/{reserva_id}/recusar", response_model=ReservaOut)
async def recusar(reserva_id: UUID, dados: RecusaIn, ctx: _com(Permissao.RESERVA_APROVAR)):
    return await service.recusar(ctx, reserva_id, dados.motivo)


@router.post("/{reserva_id}/cancelar", response_model=ReservaOut)
async def cancelar(reserva_id: UUID, ctx: _com(Permissao.RESERVA_CANCELAR)):
    return await service.cancelar(ctx, reserva_id)
