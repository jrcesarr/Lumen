# 0002. Monolito modular, um pacote por contexto

**Contexto.** Na SmartFit as pastas sao por camada (`models/`, `routers/`...), e uma feature fica espalhada pelo projeto inteiro.

**Decisao.** Um deploy so, com um pacote por contexto de negocio (identidade, carteira, reservas...).

**Consequencias.** Quem pega uma tarefa de reservas mexe so em `app/reservas/`. PRs menores e revisao mais facil. Se um contexto crescer muito, ja esta isolado para virar servico.
