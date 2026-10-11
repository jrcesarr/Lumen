"""Interface do provedor de LLM.

Escolha atual: Claude Haiku, com GPT-5.6 Luna como plano B (ver docs/decisoes/0005).
Ainda nao ha provedor real implementado. O resto do codigo depende so deste Protocol:
trocar de provedor = escrever uma nova classe, sem mexer nos contextos.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Mensagem:
    papel: str  # "sistema" | "usuario" | "assistente"
    conteudo: str


class ProvedorLLM(Protocol):
    async def completar(self, mensagens: list[Mensagem], *, max_tokens: int = 1024) -> str: ...


class ProvedorFalso:
    """Usado em dev e testes: responde sem chamar nenhuma API paga."""

    async def completar(self, mensagens: list[Mensagem], *, max_tokens: int = 1024) -> str:
        return f"[resposta simulada para: {mensagens[-1].conteudo[:60]}]"


def get_provedor() -> ProvedorLLM:
    return ProvedorFalso()
