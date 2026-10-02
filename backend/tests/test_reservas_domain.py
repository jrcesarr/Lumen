"""Regras puras: nenhum banco, nenhuma requisicao. Rodam em milissegundos."""

from datetime import UTC, datetime, timedelta

import pytest

from app.reservas.domain import (
    RegrasDaArea,
    Status,
    validar_cancelamento,
    validar_decisao,
    validar_recusa,
    validar_solicitacao,
)
from app.shared.errors import RegraDeNegocioError

AGORA = datetime(2026, 10, 10, 12, tzinfo=UTC)
AMANHA = AGORA + timedelta(days=1)
SALAO = RegrasDaArea(
    ativa=True, exige_aprovacao=True, antecedencia_min_horas=24, duracao_max_horas=6
)


def test_pedido_valido_fica_pendente():
    assert validar_solicitacao(SALAO, AMANHA, AMANHA + timedelta(hours=4), AGORA) is Status.PENDENTE


def test_area_sem_aprovacao_ja_nasce_aprovada():
    livre = RegrasDaArea(True, False, 0, 2)
    assert validar_solicitacao(livre, AMANHA, AMANHA + timedelta(hours=1), AGORA) is Status.APROVADA


@pytest.mark.parametrize(
    ("inicio", "fim", "trecho"),
    [
        (AMANHA, AMANHA, "depois do inicio"),
        (AMANHA, AMANHA - timedelta(hours=1), "depois do inicio"),
        (AMANHA, AMANHA + timedelta(hours=7), "no maximo 6 horas"),
        (AGORA + timedelta(hours=23), AGORA + timedelta(hours=25), "24 horas de antecedencia"),
    ],
)
def test_pedidos_invalidos(inicio, fim, trecho):
    with pytest.raises(RegraDeNegocioError, match=trecho):
        validar_solicitacao(SALAO, inicio, fim, AGORA)


def test_area_inativa():
    inativa = RegrasDaArea(False, True, 0, 6)
    with pytest.raises(RegraDeNegocioError, match="nao esta disponivel"):
        validar_solicitacao(inativa, AMANHA, AMANHA + timedelta(hours=1), AGORA)


def test_duracao_exatamente_no_limite_e_aceita():
    validar_solicitacao(SALAO, AMANHA, AMANHA + timedelta(hours=6), AGORA)


@pytest.mark.parametrize("status", [Status.APROVADA, Status.RECUSADA, Status.CANCELADA])
def test_so_pendente_pode_ser_decidida(status):
    with pytest.raises(RegraDeNegocioError, match="So reservas pendentes"):
        validar_decisao(status, AMANHA, AGORA)


def test_nao_decide_reserva_que_ja_comecou():
    with pytest.raises(RegraDeNegocioError, match="ja comecou"):
        validar_decisao(Status.PENDENTE, AGORA - timedelta(minutes=1), AGORA)


def test_recusa_exige_motivo():
    with pytest.raises(RegraDeNegocioError):
        validar_recusa("   ")
    assert validar_recusa("  Manutencao  ") == "Manutencao"


@pytest.mark.parametrize("status", [Status.PENDENTE, Status.APROVADA])
def test_cancela_pendente_ou_aprovada(status):
    validar_cancelamento(status, AMANHA, AGORA)


@pytest.mark.parametrize("status", [Status.RECUSADA, Status.CANCELADA])
def test_nao_cancela_recusada_nem_cancelada(status):
    with pytest.raises(RegraDeNegocioError, match="nao pode ser cancelada"):
        validar_cancelamento(status, AMANHA, AGORA)
