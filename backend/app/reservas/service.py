"""Casos de uso das reservas: busca no banco, aplica o domain.py e grava.

A RLS ja limita tudo ao condominio ativo; aqui ficam as regras mais finas
(o morador so mexe nas reservas da propria unidade).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.carteira.models import AreaComum
from app.core.permissions import Permissao
from app.reservas import domain
from app.reservas.domain import Status
from app.reservas.models import Reserva
from app.reservas.schemas import ReservaIn
from app.shared.context import RequestContext
from app.shared.errors import (
    ConflitoError,
    NaoEncontradoError,
    PermissaoNegadaError,
)
from app.shared.ids import uuid7

HORARIO_OCUPADO = "Ja existe uma reserva aprovada nesse horario para esta area"


def _agora() -> datetime:
    return datetime.now(UTC)


async def _existe_aprovada_no_horario(ctx: RequestContext, reserva: Reserva) -> bool:
    """Checagem amigavel, so para dar uma mensagem clara. Quem GARANTE e o banco."""
    consulta = select(func.count()).where(
        Reserva.area_id == reserva.area_id,
        Reserva.status == Status.APROVADA,
        Reserva.id != reserva.id,
        Reserva.inicio < reserva.fim,
        Reserva.fim > reserva.inicio,
    )
    return (await ctx.session.scalar(consulta)) > 0


async def _gravar(ctx: RequestContext) -> None:
    try:
        async with ctx.session.begin_nested():
            await ctx.session.flush()
    except IntegrityError as erro:
        # 23P01 = exclusion_violation: outra reserva foi aprovada nesse horario
        # entre a nossa checagem e a gravacao (ex.: dois sindicos ao mesmo tempo).
        if getattr(erro.orig, "sqlstate", None) == "23P01":
            raise ConflitoError(HORARIO_OCUPADO) from erro
        raise


async def solicitar(ctx: RequestContext, dados: ReservaIn) -> Reserva:
    if dados.unidade_id not in ctx.unidades_ids:
        raise PermissaoNegadaError("Voce so pode reservar para a sua propria unidade")

    area = await ctx.session.get(AreaComum, dados.area_id)
    if area is None:  # inexistente ou de outro condominio (a RLS esconde)
        raise NaoEncontradoError("Area comum nao encontrada")

    agora = _agora()
    regras = domain.RegrasDaArea(
        ativa=area.ativo,
        exige_aprovacao=area.exige_aprovacao,
        antecedencia_min_horas=area.antecedencia_min_horas,
        duracao_max_horas=area.duracao_max_horas,
    )
    status = domain.validar_solicitacao(regras, dados.inicio, dados.fim, agora)

    reserva = Reserva(
        id=uuid7(),  # ja precisamos do id na checagem de sobreposicao abaixo
        condominio_id=ctx.condominio_id,
        area_id=area.id,
        unidade_id=dados.unidade_id,
        solicitada_por=ctx.usuario_id,
        inicio=dados.inicio,
        fim=dados.fim,
        status=status,
        decidida_em=agora if status is Status.APROVADA else None,
    )
    # Nao adianta pedir um horario que ja esta tomado, mesmo que fique pendente.
    if await _existe_aprovada_no_horario(ctx, reserva):
        raise ConflitoError(HORARIO_OCUPADO)
    ctx.session.add(reserva)
    await _gravar(ctx)
    return reserva


async def listar(
    ctx: RequestContext,
    *,
    de: datetime | None = None,
    ate: datetime | None = None,
    status: Status | None = None,
) -> list[Reserva]:
    consulta = select(Reserva).order_by(Reserva.inicio)
    if ctx.pode(Permissao.RESERVA_LER_TODAS):
        pass
    elif ctx.pode(Permissao.RESERVA_LER_PROPRIAS):
        consulta = consulta.where(Reserva.unidade_id.in_(ctx.unidades_ids))
    else:
        raise PermissaoNegadaError()
    if de:
        consulta = consulta.where(Reserva.fim > de)
    if ate:
        consulta = consulta.where(Reserva.inicio < ate)
    if status:
        consulta = consulta.where(Reserva.status == status)
    return list((await ctx.session.scalars(consulta)).all())


async def _carregar(ctx: RequestContext, reserva_id: UUID) -> Reserva:
    # FOR UPDATE: trava a linha ate o fim da transacao. Se dois pedidos tentarem
    # mudar a mesma reserva juntos, o segundo espera e ve o status ja atualizado.
    reserva = await ctx.session.scalar(
        select(Reserva).where(Reserva.id == reserva_id).with_for_update()
    )
    if reserva is None:
        raise NaoEncontradoError("Reserva nao encontrada")
    return reserva


async def aprovar(ctx: RequestContext, reserva_id: UUID) -> Reserva:
    reserva = await _carregar(ctx, reserva_id)
    agora = _agora()
    domain.validar_decisao(Status(reserva.status), reserva.inicio, agora)
    if await _existe_aprovada_no_horario(ctx, reserva):
        raise ConflitoError(HORARIO_OCUPADO)
    reserva.status = Status.APROVADA
    reserva.decidida_por = ctx.usuario_id
    reserva.decidida_em = agora
    await _gravar(ctx)
    return reserva


async def recusar(ctx: RequestContext, reserva_id: UUID, motivo: str) -> Reserva:
    reserva = await _carregar(ctx, reserva_id)
    agora = _agora()
    domain.validar_decisao(Status(reserva.status), reserva.inicio, agora)
    reserva.status = Status.RECUSADA
    reserva.motivo_recusa = domain.validar_recusa(motivo)
    reserva.decidida_por = ctx.usuario_id
    reserva.decidida_em = agora
    await _gravar(ctx)
    return reserva


async def cancelar(ctx: RequestContext, reserva_id: UUID) -> Reserva:
    reserva = await _carregar(ctx, reserva_id)
    # Sindico cancela qualquer uma; morador, so as da propria unidade.
    eh_dono = reserva.unidade_id in ctx.unidades_ids
    if not eh_dono and not ctx.pode(Permissao.RESERVA_APROVAR):
        raise NaoEncontradoError("Reserva nao encontrada")  # nao revela que existe
    agora = _agora()
    domain.validar_cancelamento(Status(reserva.status), reserva.inicio, agora)
    reserva.status = Status.CANCELADA
    reserva.cancelada_em = agora
    await _gravar(ctx)
    return reserva
