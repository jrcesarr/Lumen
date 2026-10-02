# Reservas

Reservas de areas comuns: solicitar, aprovar, cancelar. Regra-chave: duas reservas aprovadas nunca se sobrepoem (exclusion constraint no banco). Proximo PR.

Estrutura quando for implementado: `models.py` (tabelas), `schemas.py` (contratos da API), `domain.py` (regras puras, sem banco), `service.py` (casos de uso), `router.py` (endpoints).
