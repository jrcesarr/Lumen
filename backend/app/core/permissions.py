"""Catalogo de permissoes no formato recurso.acao.

O enum e a fonte da verdade do vocabulario: o .value de cada membro e exatamente o
texto gravado em papel_permissoes.permissao. Cada contexto acrescenta as suas
permissoes aqui quando for implementado.
"""

from enum import StrEnum


class Permissao(StrEnum):
    # Carteira
    CONDOMINIO_LER = "condominio.ler"
    UNIDADE_LER = "unidade.ler"
    UNIDADE_GERENCIAR = "unidade.gerenciar"
    AREA_COMUM_LER = "area_comum.ler"
    AREA_COMUM_GERENCIAR = "area_comum.gerenciar"

    # Identidade
    VINCULO_LER = "vinculo.ler"
    VINCULO_GERENCIAR = "vinculo.gerenciar"

    # Reservas
    RESERVA_SOLICITAR = "reserva.solicitar"
    RESERVA_LER_PROPRIAS = "reserva.ler_proprias"
    RESERVA_LER_TODAS = "reserva.ler_todas"
    RESERVA_APROVAR = "reserva.aprovar"
    RESERVA_CANCELAR = "reserva.cancelar"

    # Auditoria
    AUDITORIA_LER = "auditoria.ler"


# Papeis do sistema e suas permissoes. Usado pela migration de seed.
P = Permissao
PAPEIS: dict[str, set[Permissao]] = {
    "morador": {
        P.CONDOMINIO_LER,
        P.AREA_COMUM_LER,
        P.RESERVA_SOLICITAR,
        P.RESERVA_LER_PROPRIAS,
        P.RESERVA_CANCELAR,
    },
    "sindico": {
        P.CONDOMINIO_LER,
        P.UNIDADE_LER,
        P.AREA_COMUM_LER,
        P.AREA_COMUM_GERENCIAR,
        P.VINCULO_LER,
        P.RESERVA_LER_TODAS,
        P.RESERVA_APROVAR,
        P.RESERVA_CANCELAR,
        P.AUDITORIA_LER,
    },
    "porteiro": {P.CONDOMINIO_LER, P.UNIDADE_LER},
    "prestador": {P.CONDOMINIO_LER},
    "atendente": {
        P.CONDOMINIO_LER,
        P.UNIDADE_LER,
        P.AREA_COMUM_LER,
        P.VINCULO_LER,
        P.RESERVA_LER_TODAS,
    },
    "admin": set(Permissao),
}
