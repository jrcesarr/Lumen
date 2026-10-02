import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import psycopg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.reservas import service
from app.shared.context import montar_contexto
from app.shared.errors import ConflitoError
from tests.factories import criar_cenario, headers

# Sempre no futuro e alinhado na hora cheia, para respeitar a antecedencia de 24h.
BASE = (datetime.now(UTC) + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)


def _periodo(h_inicio: int, h_fim: int) -> dict[str, str]:
    return {
        "inicio": (BASE + timedelta(hours=h_inicio)).isoformat(),
        "fim": (BASE + timedelta(hours=h_fim)).isoformat(),
    }


async def _pedir(client, c, usuario, unidade, h_inicio=14, h_fim=18, cond=None):
    corpo = {"area_id": str(c.area_a), "unidade_id": str(unidade), **_periodo(h_inicio, h_fim)}
    return await client.post("/api/v1/reservas", json=corpo, headers=headers(usuario, cond))


async def test_morador_solicita_e_fica_pendente(admin, client):
    c = criar_cenario(admin)
    resposta = await _pedir(client, c, c.morador_a, c.unidade_a101)
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "pendente"


async def test_morador_nao_reserva_para_unidade_alheia(admin, client):
    c = criar_cenario(admin)
    resposta = await _pedir(client, c, c.morador_a, c.unidade_a102)
    assert resposta.status_code == 403


async def test_area_de_outro_condominio_nao_existe_para_mim(admin, client):
    c = criar_cenario(admin)
    corpo = {"area_id": str(c.area_b), "unidade_id": str(c.unidade_a101), **_periodo(14, 18)}
    resposta = await client.post("/api/v1/reservas", json=corpo, headers=headers(c.morador_a))
    assert resposta.status_code == 404


async def test_regra_de_negocio_vira_422(admin, client):
    c = criar_cenario(admin)
    resposta = await _pedir(client, c, c.morador_a, c.unidade_a101, 14, 22)  # 8h > max 6h
    assert resposta.status_code == 422
    assert "no maximo 6 horas" in resposta.json()["detail"]


async def test_horario_sem_fuso_e_recusado(admin, client):
    c = criar_cenario(admin)
    corpo = {
        "area_id": str(c.area_a),
        "unidade_id": str(c.unidade_a101),
        "inicio": "2030-01-01T14:00:00",
        "fim": "2030-01-01T18:00:00",
    }
    resposta = await client.post("/api/v1/reservas", json=corpo, headers=headers(c.morador_a))
    assert resposta.status_code == 422


async def test_fluxo_aprovar_e_bloquear_horario(admin, client):
    c = criar_cenario(admin)
    r1 = (await _pedir(client, c, c.morador_a, c.unidade_a101)).json()
    aprovada = await client.post(
        f"/api/v1/reservas/{r1['id']}/aprovar", headers=headers(c.sindico_a)
    )
    assert aprovada.json()["status"] == "aprovada"

    # Outro morador tenta o mesmo horario (sobrepondo 1h): bloqueado logo no pedido.
    outro = await _pedir(client, c, c.multi, c.unidade_a102, 17, 20, cond=c.cond_a)
    assert outro.status_code == 409


async def test_horarios_encostados_nao_colidem(admin, client):
    """14h-18h e 18h-22h: o intervalo e [inicio, fim), entao 18h pertence so ao segundo."""
    c = criar_cenario(admin)
    for unidade, usuario, ini, fim in [
        (c.unidade_a101, c.morador_a, 12, 18),
        (c.unidade_a102, c.multi, 18, 22),
    ]:
        r = (await _pedir(client, c, usuario, unidade, ini, fim, cond=c.cond_a)).json()
        aprovada = await client.post(
            f"/api/v1/reservas/{r['id']}/aprovar", headers=headers(c.sindico_a)
        )
        assert aprovada.status_code == 200


async def test_dois_sindicos_aprovando_ao_mesmo_tempo(admin, client, engine):
    """A corrida que so o banco resolve.

    O sindico 1 aprova a reserva A e, ANTES de ele confirmar (commit), o sindico 2 aprova
    a reserva B, que se sobrepoe. A checagem amigavel do sindico 2 nao ve nada aprovado
    (o commit do 1 ainda nao aconteceu), entao so a exclusion constraint pode barrar.
    O banco faz o sindico 2 esperar e, quando o 1 confirma, recusa o 2 com 409.
    """
    c = criar_cenario(admin)
    r1 = (await _pedir(client, c, c.morador_a, c.unidade_a101, 14, 18)).json()
    r2 = (await _pedir(client, c, c.multi, c.unidade_a102, 16, 20, cond=c.cond_a)).json()

    async def aprovar_como_sindico(reserva_id, request_id):
        async with AsyncSession(engine) as sessao:
            async with montar_contexto(sessao, c.sindico_a, c.cond_a, request_id) as ctx:
                return await service.aprovar(ctx, UUID(reserva_id))

    async with AsyncSession(engine) as sessao1:
        async with montar_contexto(sessao1, c.sindico_a, c.cond_a, "sindico-1") as ctx1:
            await service.aprovar(ctx1, UUID(r1["id"]))  # gravou, mas sem commit
            segundo = asyncio.create_task(aprovar_como_sindico(r2["id"], "sindico-2"))
            await asyncio.sleep(0.5)
            assert not segundo.done(), "o banco deveria segurar o sindico 2 esperando"
        # aqui o sindico 1 faz commit

    with pytest.raises(ConflitoError):
        await segundo
    aprovadas = admin.execute("SELECT count(*) FROM reservas WHERE status = 'aprovada'").fetchone()
    assert aprovadas == (1,)


async def test_recusa_precisa_de_motivo(admin, client):
    c = criar_cenario(admin)
    r = (await _pedir(client, c, c.morador_a, c.unidade_a101)).json()
    url = f"/api/v1/reservas/{r['id']}/recusar"
    assert (
        await client.post(url, json={"motivo": ""}, headers=headers(c.sindico_a))
    ).status_code == 422
    recusada = await client.post(url, json={"motivo": "Dedetizacao"}, headers=headers(c.sindico_a))
    assert recusada.json() == {
        **recusada.json(),
        "status": "recusada",
        "motivo_recusa": "Dedetizacao",
    }
    # Ja decidida: nao pode aprovar depois.
    aprovar = await client.post(f"/api/v1/reservas/{r['id']}/aprovar", headers=headers(c.sindico_a))
    assert aprovar.status_code == 422


async def test_morador_nao_aprova(admin, client):
    c = criar_cenario(admin)
    r = (await _pedir(client, c, c.morador_a, c.unidade_a101)).json()
    resposta = await client.post(
        f"/api/v1/reservas/{r['id']}/aprovar", headers=headers(c.morador_a)
    )
    assert resposta.status_code == 403


async def test_quem_ve_o_que(admin, client):
    c = criar_cenario(admin)
    await _pedir(client, c, c.morador_a, c.unidade_a101, 10, 12)
    await _pedir(client, c, c.multi, c.unidade_a102, 14, 16, cond=c.cond_a)

    do_morador = (await client.get("/api/v1/reservas", headers=headers(c.morador_a))).json()
    do_sindico = (await client.get("/api/v1/reservas", headers=headers(c.sindico_a))).json()
    do_b = (await client.get("/api/v1/reservas", headers=headers(c.morador_b))).json()
    assert [r["unidade_id"] for r in do_morador] == [str(c.unidade_a101)]
    assert len(do_sindico) == 2
    assert do_b == []


async def test_cancelamento(admin, client):
    c = criar_cenario(admin)
    r = (await _pedir(client, c, c.morador_a, c.unidade_a101)).json()
    url = f"/api/v1/reservas/{r['id']}/cancelar"
    # Outro morador do mesmo predio nao enxerga a reserva alheia.
    assert (await client.post(url, headers=headers(c.multi, c.cond_a))).status_code == 404
    cancelada = await client.post(url, headers=headers(c.morador_a))
    assert cancelada.json()["status"] == "cancelada"


async def test_auditoria_registra_quem_aprovou(admin, client):
    c = criar_cenario(admin)
    r = (await _pedir(client, c, c.morador_a, c.unidade_a101)).json()
    await client.post(f"/api/v1/reservas/{r['id']}/aprovar", headers=headers(c.sindico_a))
    linhas = admin.execute(
        "SELECT acao, ator_id, ator_papel FROM auditoria WHERE tabela = 'reservas' ORDER BY id"
    ).fetchall()
    assert linhas == [("insert", c.morador_a, "morador"), ("update", c.sindico_a, "sindico")]


def test_banco_barra_sobreposicao_mesmo_sem_a_api(admin):
    """Ultima linha de defesa: nem um INSERT direto consegue duas aprovadas sobrepostas."""
    c = criar_cenario(admin)
    sql = (
        "INSERT INTO reservas (id, condominio_id, area_id, unidade_id, solicitada_por,"
        " inicio, fim, status, decidida_em)"
        " VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, 'aprovada', now())"
    )
    admin.execute(
        sql, (c.cond_a, c.area_a, c.unidade_a101, c.morador_a, BASE, BASE + timedelta(hours=4))
    )
    with pytest.raises(psycopg.errors.ExclusionViolation):
        admin.execute(
            sql,
            (
                c.cond_a,
                c.area_a,
                c.unidade_a102,
                c.multi,
                BASE + timedelta(hours=3),
                BASE + timedelta(hours=5),
            ),
        )


def test_reserva_nao_aponta_para_area_de_outro_condominio(admin):
    c = criar_cenario(admin)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        admin.execute(
            "INSERT INTO reservas (id, condominio_id, area_id, unidade_id, solicitada_por,"
            " inicio, fim) VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s)",
            (c.cond_a, c.area_b, c.unidade_a101, c.morador_a, BASE, BASE + timedelta(hours=1)),
        )
