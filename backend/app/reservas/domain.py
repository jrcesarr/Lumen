"""Regras de negocio das reservas, sem banco e sem FastAPI.

Funcoes puras: recebem dados e devolvem o novo estado ou levantam RegraDeNegocioError.
Por isso os testes delas rodam em milissegundos (tests/test_reservas_domain.py).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.shared.errors import RegraDeNegocioError


class Status(StrEnum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"
    RECUSADA = "recusada"
    CANCELADA = "cancelada"


@dataclass(frozen=True)
class RegrasDaArea:
    ativa: bool
    exige_aprovacao: bool
    antecedencia_min_horas: int
    duracao_max_horas: int


def validar_solicitacao(
    area: RegrasDaArea, inicio: datetime, fim: datetime, agora: datetime
) -> Status:
    """Confere o pedido e devolve o status inicial da reserva."""
    if not area.ativa:
        raise RegraDeNegocioError("Esta area comum nao esta disponivel para reservas")
    if fim <= inicio:
        raise RegraDeNegocioError("O fim da reserva precisa ser depois do inicio")
    if fim - inicio > timedelta(hours=area.duracao_max_horas):
        raise RegraDeNegocioError(f"A reserva pode durar no maximo {area.duracao_max_horas} horas")
    if inicio - agora < timedelta(hours=area.antecedencia_min_horas):
        raise RegraDeNegocioError(
            f"Reserve com pelo menos {area.antecedencia_min_horas} horas de antecedencia"
        )
    # Area sem aprovacao (ex.: churrasqueira de uso livre): ja nasce aprovada.
    return Status.PENDENTE if area.exige_aprovacao else Status.APROVADA


def validar_decisao(status: Status, inicio: datetime, agora: datetime) -> None:
    """Aprovar ou recusar: so pedidos pendentes e que ainda nao comecaram."""
    if status is not Status.PENDENTE:
        raise RegraDeNegocioError(f"So reservas pendentes podem ser decididas (esta: {status})")
    if inicio <= agora:
        raise RegraDeNegocioError("Esta reserva ja comecou e nao pode mais ser decidida")


def validar_recusa(motivo: str | None) -> str:
    if not motivo or not motivo.strip():
        raise RegraDeNegocioError("Informe o motivo da recusa")
    return motivo.strip()


def validar_cancelamento(status: Status, inicio: datetime, agora: datetime) -> None:
    if status not in (Status.PENDENTE, Status.APROVADA):
        raise RegraDeNegocioError(f"Uma reserva {status} nao pode ser cancelada")
    if inicio <= agora:
        raise RegraDeNegocioError("Nao da para cancelar uma reserva que ja comecou")
