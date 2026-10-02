"""Contexto da requisicao: quem e o usuario, em qual condominio esta e o que pode fazer.

Todo endpoint de negocio recebe um RequestContext, e nunca uma sessao de banco solta.
Assim e impossivel esquecer de "carimbar" a transacao (GUCs) antes de acessar dados:
sem carimbo, a RLS devolve zero linhas (falha fechada).

Diferenca em relacao a SmartFit: la cada usuario tem um vinculo so. Na Lumen, uma pessoa
pode ser moradora de um condominio e sindica de outro, entao o front informa o condominio
ativo no header X-Condominio-Id (ver docs/decisoes/0004).
"""

import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permissao
from app.core.security import UsuarioAutenticado, decodificar_token_async
from app.shared.db import DbSession
from app.shared.errors import AppError, NaoAutenticadoError, PermissaoNegadaError

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)

_PERMISSOES_VALIDAS = {p.value for p in Permissao}


class CondominioNaoSelecionadoError(AppError):
    status_code = 400

    def __init__(self) -> None:
        super().__init__("Usuario tem vinculo com mais de um condominio: envie X-Condominio-Id")


@dataclass
class RequestContext:
    session: AsyncSession
    usuario_id: UUID
    condominio_id: UUID
    papeis: set[str]
    permissoes: set[Permissao]
    unidades_ids: set[UUID] = field(default_factory=set)

    def pode(self, permissao: Permissao) -> bool:
        return permissao in self.permissoes

    def alcanca_unidade(self, unidade_id: UUID) -> bool:
        # Quem le "todas" (sindico, atendente) alcanca qualquer unidade do condominio;
        # o morador so as unidades dos proprios vinculos.
        return self.pode(Permissao.UNIDADE_LER) or unidade_id in self.unidades_ids


async def usuario_atual(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UsuarioAutenticado:
    if credenciais is None:
        raise NaoAutenticadoError()
    return await decodificar_token_async(credenciais.credentials)


UsuarioAtualDep = Annotated[UsuarioAutenticado, Depends(usuario_atual)]


async def _carimbar(session: AsyncSession, **gucs: str) -> None:
    # set_config(..., true) vale so ate o fim da transacao (equivale a SET LOCAL),
    # o que e seguro com pooler em modo transaction.
    partes = ", ".join(f"set_config('app.{nome}', :{nome}, true)" for nome in gucs)
    await session.execute(text(f"SELECT {partes}"), gucs)


@asynccontextmanager
async def montar_contexto(
    session: AsyncSession,
    usuario_id: UUID,
    condominio_id: UUID | None,
    request_id: str,
) -> AsyncGenerator[RequestContext, None]:
    """Nucleo do contexto, sem depender do FastAPI (reaproveitavel pelos jobs)."""
    async with session.begin():
        # 1) Carimba so o usuario: a policy de vinculos deixa cada um ler os proprios.
        await _carimbar(session, usuario_id=str(usuario_id), request_id=request_id)
        linhas = (
            await session.execute(
                text(
                    """
                    SELECT v.condominio_id, v.papel, v.unidade_id, pp.permissao
                      FROM vinculos v
                      LEFT JOIN papel_permissoes pp ON pp.papel = v.papel
                     WHERE v.usuario_id = :usuario AND v.ativo
                    """
                ),
                {"usuario": usuario_id},
            )
        ).all()

        condominios = {linha.condominio_id for linha in linhas}
        if not condominios:
            raise PermissaoNegadaError("Usuario sem vinculo ativo com nenhum condominio")
        if condominio_id is None:
            if len(condominios) > 1:
                raise CondominioNaoSelecionadoError()
            condominio_id = next(iter(condominios))
        elif condominio_id not in condominios:
            raise PermissaoNegadaError("Usuario sem vinculo com este condominio")

        do_condominio = [linha for linha in linhas if linha.condominio_id == condominio_id]
        papeis = {linha.papel for linha in do_condominio}
        unidades = {linha.unidade_id for linha in do_condominio if linha.unidade_id}
        permissoes: set[Permissao] = set()
        for linha in do_condominio:
            if linha.permissao is None:
                continue
            if linha.permissao in _PERMISSOES_VALIDAS:
                permissoes.add(Permissao(linha.permissao))
            else:
                # Falha fechada: permissao desconhecida e ignorada, nao concedida.
                logger.warning("Permissao fora do catalogo", extra={"permissao": linha.permissao})

        # 2) Carimba o condominio ativo e os papeis (usados pela RLS e pela auditoria).
        await _carimbar(
            session,
            condominio_id=str(condominio_id),
            papel=",".join(sorted(papeis)),
        )
        yield RequestContext(
            session=session,
            usuario_id=usuario_id,
            condominio_id=condominio_id,
            papeis=papeis,
            permissoes=permissoes,
            unidades_ids=unidades,
        )


async def get_request_context(
    request: Request,
    usuario: UsuarioAtualDep,
    session: DbSession,
    x_condominio_id: Annotated[UUID | None, Header()] = None,
) -> AsyncGenerator[RequestContext, None]:
    async with montar_contexto(
        session, UUID(usuario.id), x_condominio_id, request.state.request_id
    ) as ctx:
        yield ctx


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]


def RequirePermission(permissao: Permissao) -> Callable[..., RequestContext]:  # noqa: N802
    """Uso: ctx: RequestContext = Depends(RequirePermission(Permissao.RESERVA_APROVAR))."""

    def verificar(ctx: RequestContextDep) -> RequestContext:
        if not ctx.pode(permissao):
            raise PermissaoNegadaError()
        return ctx

    return verificar


async def get_sessao_do_usuario(
    request: Request, usuario: UsuarioAtualDep, session: DbSession
) -> AsyncGenerator[tuple[AsyncSession, UUID], None]:
    """Sessao carimbada so com o usuario, sem condominio ativo.

    Usada apenas por GET /me, que lista os vinculos para o seletor de condominio.
    """
    async with session.begin():
        await _carimbar(session, usuario_id=usuario.id, request_id=request.state.request_id)
        yield session, UUID(usuario.id)


SessaoDoUsuarioDep = Annotated[tuple[AsyncSession, UUID], Depends(get_sessao_do_usuario)]
