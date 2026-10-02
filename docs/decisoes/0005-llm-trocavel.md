# 0005. Provedor de LLM atras de uma interface

**Contexto.** O provedor de IA ainda nao foi escolhido (custo, qualidade em portugues e privacidade estao em avaliacao).

**Decisao.** Todo uso de IA passa por `ProvedorLLM` em `app/inteligencia/llm.py`. Em dev e testes, um provedor falso.

**Consequencias.** A escolha pode ficar para depois sem travar o resto. Trocar de provedor e escrever uma classe nova.
