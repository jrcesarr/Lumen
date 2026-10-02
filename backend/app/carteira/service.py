"""Casos de uso da Carteira. Recebem o RequestContext: a RLS ja filtra pelo condominio."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.carteira.models import AreaComum, Unidade
from app.carteira.schemas import AreaComumIn
from app.core.permissions import Permissao
from app.shared.context import RequestContext
from app.shared.errors import ConflitoError


async def listar_unidades(ctx: RequestContext) -> list[Unidade]:
    consulta = select(Unidade).where(Unidade.ativo).order_by(Unidade.bloco, Unidade.numero)
    # Morador ve so as proprias unidades; sindico/portaria veem todas do condominio.
    if not ctx.pode(Permissao.UNIDADE_LER):
        consulta = consulta.where(Unidade.id.in_(ctx.unidades_ids))
    return list((await ctx.session.scalars(consulta)).all())


async def listar_areas(ctx: RequestContext) -> list[AreaComum]:
    consulta = select(AreaComum).where(AreaComum.ativo).order_by(AreaComum.nome)
    return list((await ctx.session.scalars(consulta)).all())


async def criar_area(ctx: RequestContext, dados: AreaComumIn) -> AreaComum:
    area = AreaComum(condominio_id=ctx.condominio_id, **dados.model_dump())
    ctx.session.add(area)
    try:
        # SAVEPOINT: se o nome repetir, so este insert e desfeito.
        async with ctx.session.begin_nested():
            await ctx.session.flush()
    except IntegrityError as erro:
        raise ConflitoError("Ja existe uma area comum com esse nome") from erro
    return area
