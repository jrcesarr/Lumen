from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.carteira.models import Condominio
from app.identidade.models import Usuario, Vinculo
from app.identidade.schemas import MeOut, VinculoOut
from app.shared.errors import NaoEncontradoError


async def obter_me(session: AsyncSession, usuario_id: UUID) -> MeOut:
    usuario = await session.get(Usuario, usuario_id)
    if usuario is None:
        # Logou no Supabase mas o perfil ainda nao foi criado (ver trigger da migration 002).
        raise NaoEncontradoError("Perfil de usuario nao encontrado")

    linhas = await session.execute(
        select(Vinculo, Condominio.nome)
        .join(Condominio, Condominio.id == Vinculo.condominio_id)
        .where(Vinculo.usuario_id == usuario_id, Vinculo.ativo)
        .order_by(Condominio.nome)
    )
    vinculos = [
        VinculoOut(
            condominio_id=v.condominio_id,
            condominio_nome=nome,
            papel=v.papel,
            unidade_id=v.unidade_id,
        )
        for v, nome in linhas.all()
    ]
    return MeOut(id=usuario.id, nome=usuario.nome, email=usuario.email, vinculos=vinculos)
