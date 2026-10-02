from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.carteira import service
from app.carteira.schemas import AreaComumIn, AreaComumOut, UnidadeOut
from app.core.permissions import Permissao
from app.shared.context import RequestContext, RequestContextDep, RequirePermission

router = APIRouter(tags=["carteira"])


@router.get("/unidades", response_model=list[UnidadeOut])
async def listar_unidades(ctx: RequestContextDep):
    return await service.listar_unidades(ctx)


@router.get("/areas-comuns", response_model=list[AreaComumOut])
async def listar_areas(
    ctx: Annotated[RequestContext, Depends(RequirePermission(Permissao.AREA_COMUM_LER))],
):
    return await service.listar_areas(ctx)


@router.post("/areas-comuns", response_model=AreaComumOut, status_code=status.HTTP_201_CREATED)
async def criar_area(
    dados: AreaComumIn,
    ctx: Annotated[RequestContext, Depends(RequirePermission(Permissao.AREA_COMUM_GERENCIAR))],
):
    return await service.criar_area(ctx, dados)
