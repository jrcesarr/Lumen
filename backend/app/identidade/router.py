from fastapi import APIRouter

from app.identidade import service
from app.identidade.schemas import MeOut
from app.shared.context import SessaoDoUsuarioDep

router = APIRouter(tags=["identidade"])


@router.get("/me", response_model=MeOut)
async def me(sessao: SessaoDoUsuarioDep):
    """Quem sou eu e em quais condominios tenho vinculo (alimenta o seletor do front)."""
    session, usuario_id = sessao
    return await service.obter_me(session, usuario_id)
