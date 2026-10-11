# 0005. Provedor de LLM atras de uma interface

**Contexto.** A Lumen usa IA em dois pontos: o assistente do regimento e a leitura de notas fiscais. Os criterios sao custo, qualidade em portugues, confiabilidade e privacidade (LGPD).

**Decisao.** Todo uso de IA passa por `ProvedorLLM` em `app/inteligencia/llm.py`. Em dev e testes, um provedor falso. O provedor escolhido e o **Claude Haiku 5.5**, nos dois usos, pelo menor custo por token e por aceitar texto e imagem com saida estruturada. O plano B e o **GPT-5.6 Luna**. A comparacao esta em `desafio1-llm/comparativo-llm.md` (fora do repositorio). NF-e em XML nao passa pelo LLM: um parser le direto.

**Consequencias.** Ainda nao existe uma classe de provedor real: hoje so ha o provedor falso. Trocar de provedor e escrever uma classe nova, e os dois candidatos podem ser medidos com perguntas reais do regimento antes de decidir em definitivo. O assistente recebe so a pergunta e o regimento, sem dado pessoal.
