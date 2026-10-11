"""Outbox: o evento nasce junto com o fato e o worker entrega depois."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.outbox import MAX_TENTATIVAS, processar_lote
from app.shared.context import montar_contexto
from app.shared.outbox import Evento
from tests.factories import criar_cenario, headers
from tests.test_reservas_api import _pedir


def _eventos(admin):
    return admin.execute(
        "SELECT tipo, status, payload FROM outbox ORDER BY criado_em, tipo"
    ).fetchall()


async def _aprovar(client, c, reserva_id):
    return await client.post(f"/api/v1/reservas/{reserva_id}/aprovar", headers=headers(c.sindico_a))


async def test_solicitar_e_aprovar_gravam_eventos(admin, client):
    c = criar_cenario(admin)
    reserva = (await _pedir(client, c, c.morador_a, c.unidade_a101)).json()
    assert [e[0] for e in _eventos(admin)] == ["reserva.solicitada"]

    await _aprovar(client, c, reserva["id"])
    eventos = _eventos(admin)
    assert [e[0] for e in eventos] == ["reserva.solicitada", "reserva.aprovada"]
    assert all(e[1] == "pendente" for e in eventos)
    assert eventos[1][2]["reserva_id"] == reserva["id"]
    assert eventos[1][2]["unidade_id"] == str(c.unidade_a101)


async def test_recusar_leva_o_motivo(admin, client):
    c = criar_cenario(admin)
    reserva = (await _pedir(client, c, c.morador_a, c.unidade_a101)).json()
    await client.post(
        f"/api/v1/reservas/{reserva['id']}/recusar",
        json={"motivo": "Area em manutencao"},
        headers=headers(c.sindico_a),
    )
    recusada = [e for e in _eventos(admin) if e[0] == "reserva.recusada"]
    assert len(recusada) == 1
    assert recusada[0][2]["motivo"] == "Area em manutencao"


async def test_pedido_barrado_nao_deixa_evento(admin, client):
    c = criar_cenario(admin)
    r1 = (await _pedir(client, c, c.morador_a, c.unidade_a101, 14, 18)).json()
    await _aprovar(client, c, r1["id"])
    antes = len(_eventos(admin))

    conflito = await _pedir(client, c, c.multi, c.unidade_a102, 17, 20, cond=c.cond_a)
    assert conflito.status_code == 409
    assert len(_eventos(admin)) == antes


async def test_worker_entrega_e_marca_processado(admin, client, engine):
    c = criar_cenario(admin)
    await _pedir(client, c, c.morador_a, c.unidade_a101)
    recebidos: list[UUID] = []

    async def handler(evento: Evento) -> None:
        recebidos.append(evento.id)

    async with AsyncSession(engine) as sessao:
        pegou = await processar_lote(sessao, {"reserva.solicitada": handler})
    assert pegou == 1 and len(recebidos) == 1
    assert _eventos(admin)[0][1] == "processado"

    async with AsyncSession(engine) as sessao:  # nada pendente: nao entrega de novo
        assert await processar_lote(sessao, {"reserva.solicitada": handler}) == 0
    assert len(recebidos) == 1


async def test_falha_tenta_de_novo_com_espera_e_desiste_no_limite(admin, client, engine):
    c = criar_cenario(admin)
    await _pedir(client, c, c.morador_a, c.unidade_a101)

    async def quebrado(evento: Evento) -> None:
        raise RuntimeError("push fora do ar")

    agora = datetime.now(UTC)
    async with AsyncSession(engine) as sessao:
        await processar_lote(sessao, {"reserva.solicitada": quebrado}, agora=agora)
    status, tentativas, erro = admin.execute(
        "SELECT status, tentativas, ultimo_erro FROM outbox"
    ).fetchone()
    assert (status, tentativas, erro) == ("pendente", 1, "push fora do ar")

    async with AsyncSession(engine) as sessao:  # ainda dentro da espera: nao tenta
        assert await processar_lote(sessao, {"reserva.solicitada": quebrado}, agora=agora) == 0

    for _ in range(MAX_TENTATIVAS - 1):  # avanca o relogio alem de qualquer espera
        agora += timedelta(hours=2)
        async with AsyncSession(engine) as sessao:
            await processar_lote(sessao, {"reserva.solicitada": quebrado}, agora=agora)
    status, tentativas = admin.execute("SELECT status, tentativas FROM outbox").fetchone()
    assert (status, tentativas) == ("falhou", MAX_TENTATIVAS)


async def test_evento_sem_handler_conta_como_falha(admin, client, engine):
    c = criar_cenario(admin)
    await _pedir(client, c, c.morador_a, c.unidade_a101)
    async with AsyncSession(engine) as sessao:
        await processar_lote(sessao, {})
    erro = admin.execute("SELECT ultimo_erro FROM outbox").fetchone()[0]
    assert "sem handler" in erro


async def test_condominio_b_nao_ve_eventos_do_a(admin, client, engine):
    c = criar_cenario(admin)
    await _pedir(client, c, c.morador_a, c.unidade_a101)

    async with AsyncSession(engine) as sessao:
        async with montar_contexto(sessao, c.sindico_a, c.cond_a, "teste") as ctx:
            assert len((await ctx.session.scalars(select(Evento))).all()) == 1
    async with AsyncSession(engine) as sessao:
        async with montar_contexto(sessao, c.morador_b, c.cond_b, "teste") as ctx:
            assert len((await ctx.session.scalars(select(Evento))).all()) == 0


async def test_sem_carimbo_nao_ve_a_outbox(admin, client, engine):
    c = criar_cenario(admin)
    await _pedir(client, c, c.morador_a, c.unidade_a101)
    async with engine.begin() as conn:
        total = (await conn.execute(text("SELECT count(*) FROM outbox"))).scalar()
    assert total == 0
