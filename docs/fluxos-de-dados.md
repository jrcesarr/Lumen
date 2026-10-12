# Fluxo de dados por funcionalidade

Para cada funcionalidade: quais telas o usuário vê, quais endpoints do back são chamados e o que acontece por trás.
Todos os endpoints ficam sob `/api/v1`. **(no repo)** marca o que já está implementado; o resto é o plano.

Legenda dos perfis: Morador, Síndico, Porteiro, Prestador, Atendente, Administrador (equipe da Lumen).

## 0. Fluxo comum a toda requisição

| Passo | Tela | Chamada | O que acontece |
|---|---|---|---|
| 1 | Login | Supabase Auth (`signInWithPassword` ou magic link) | O Supabase devolve um JWT. A API não vê a senha |
| 2 | Seletor de condomínio (topo) | `GET /me` **(no repo)** | A API lista os vínculos do usuário: condomínios, unidades e papéis |
| 3 | Redireciona para a área do perfil (`/morador`, `/sindico`, `/portaria`...) | | O front escolhe a área pelo papel de maior acesso |
| 4 | Qualquer tela | Toda chamada leva `Authorization: Bearer <jwt>` e `X-Condominio-Id` | A API valida o JWT, confere o vínculo, checa a permissão `recurso.acao` e grava o condomínio na sessão do Postgres. O RLS filtra o resto |

Erros sempre voltam como `{detail, request_id}`. Uma regra de negócio violada responde 409, e falta de permissão responde 403.

---

## Identidade e Carteira (fase 1)

### Administrar condomínios e perfis (Administrador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Lista de condomínios | `GET /condominios` | Carteira da Lumen, com contrato e status |
| Cadastro de condomínio | `POST /condominios`, `POST /condominios/{id}/unidades` | Cria o condomínio e as unidades. Emite `CondominioCadastrado` |
| Áreas comuns | `GET /areas-comuns` **(no repo)**, `POST /areas-comuns` **(no repo)** | Áreas que poderão ser reservadas |
| Usuários e perfis | `POST /convites`, `PATCH /vinculos/{id}` | Convida por e-mail ou WhatsApp e troca o papel. Emite `UsuarioConvidado` e `PerfilAlterado` → Notificações |

---

## Reservas (fase 1)

### Reservar área comum e ver minhas reservas (Morador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Nova reserva: escolhe a área | `GET /areas-comuns` **(no repo)** | Lista as áreas do condomínio ativo |
| Calendário da área | `GET /reservas?de=&ate=&status=aprovada` **(no repo)** | Mostra os horários ocupados |
| Confirmar pedido | `POST /reservas` **(no repo)** | Cria com status `pendente`. Emite `ReservaSolicitada` → aviso ao síndico |
| Minhas reservas | `GET /reservas` **(no repo)** | O morador só vê as da própria unidade |
| Cancelar | `POST /reservas/{id}/cancelar` **(no repo)** | Libera o horário. Emite `reserva.cancelada` → aviso à outra parte (síndico ou morador) |

### Aprovar reservas e gerenciar áreas (Síndico)
| Tela | Chamada | O que acontece |
|---|---|---|
| Fila de aprovação | `GET /reservas?status=pendente` **(no repo)** | Pedidos do condomínio inteiro |
| Aprovar | `POST /reservas/{id}/aprovar` **(no repo)** | O banco barra a sobreposição (exclusion constraint) → 409. Emite `ReservaAprovada` → WhatsApp ao morador |
| Recusar com motivo | `POST /reservas/{id}/recusar` **(no repo)** | Emite `ReservaRecusada` → WhatsApp ao morador |
| Configurar áreas | `POST /areas-comuns` **(no repo)** | Nome, capacidade e regras |

> **Eventos (no repo):** `reserva.solicitada`, `reserva.aprovada`, `reserva.recusada` e `reserva.cancelada` são gravados na tabela `outbox` na mesma transação da reserva. O worker (`python -m app.jobs.worker`) entrega e tenta de novo se falhar; hoje o handler só registra no log, e o push do PWA e o WhatsApp entram com o contexto Comunicação.

---

## Chamados (fases 1 e 2)

### Abrir chamado e acompanhar (Morador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Novo chamado | `POST /arquivos/upload-url` → envio direto ao Object Storage | A API gera um link assinado e a foto vai direto para o bucket `lumen-arquivos` |
| | `POST /chamados` | Cria o chamado `aberto` com a chave da foto. Emite `ChamadoAberto` → aviso ao síndico |
| Meus chamados | `GET /chamados` | Status e histórico |
| Avaliar | `POST /chamados/{id}/avaliacao` | Nota ao prestador depois de concluído |

### Acompanhar chamados e avaliar prestadores (Síndico)
| Tela | Chamada | O que acontece |
|---|---|---|
| Painel de chamados | `GET /chamados?status=` | Todos do condomínio |
| Atribuir prestador | `POST /chamados/{id}/atribuir` | `aberto → atribuído`. Emite `ChamadoAtribuido` → WhatsApp ao prestador |
| Aprovar orçamento | `POST /orcamentos/{id}/aprovar` | Vira uma Despesa prevista no Financeiro |

### Ver e atualizar chamados; enviar orçamento e NF (Prestador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Meus chamados | `GET /chamados?atribuido_a=eu` | Só os atribuídos a ele |
| Atualizar status | `PATCH /chamados/{id}/status` | `atribuído → em andamento → concluído`. A máquina de estados recusa saltos (409) |
| Enviar orçamento | `POST /chamados/{id}/orcamentos` | Emite `OrcamentoEnviado` → aviso ao síndico |
| Enviar NF (fase 2) | upload por link assinado + `POST /documentos/notas-fiscais` | Segue para a leitura de NF (Inteligência) |

---

## Portaria (fase 1)

### Registrar encomendas e notificar (Porteiro)
| Tela | Chamada | O que acontece |
|---|---|---|
| Busca de unidade | `GET /unidades?busca=` **(no repo, sem busca)** | Poucos toques no celular |
| Registrar encomenda | `POST /encomendas` | Emite `EncomendaRegistrada` → outbox → WhatsApp ao morador |
| Pendentes / retirada | `GET /encomendas?status=pendente`, `POST /encomendas/{id}/retirada` | Emite `EncomendaRetirada` |

### Registrar visitantes e prestadores autorizados (Porteiro)
| Tela | Chamada | O que acontece |
|---|---|---|
| Novo visitante | `POST /visitas` | Emite `VisitanteRegistrado` → aviso ao morador |
| Prestadores autorizados | `GET /prestadores-autorizados` | Lista o que o síndico liberou |

O morador recebe esses avisos por WhatsApp e vê o histórico em `GET /encomendas` e `GET /visitas` (só os da unidade dele).

---

## Comunicação (fases 1 e 2)

### Publicar comunicados e convocar assembleias (Síndico) / receber (Morador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Novo comunicado | `POST /comunicados` (público: todos, bloco ou unidade) | Emite `ComunicadoPublicado` → WhatsApp para o público |
| Convocar assembleia | `POST /assembleias` | Emite `AssembleiaConvocada` |
| Mural (Morador) | `GET /comunicados` | Só os do seu público |

### Mensagens: síndico, morador e atendente (fase 2)
| Tela | Chamada | O que acontece |
|---|---|---|
| Caixa de conversas | `GET /conversas` | Lista conversas do usuário |
| Chat aberto | `GET /conversas/{id}/mensagens` + WebSocket `/ws/conversas/{id}` | Mensagens em tempo real pela própria API |
| Enviar | `POST /conversas/{id}/mensagens` | Emite `MensagemEnviada` → push ou WhatsApp se offline |
| Encaminhar ao administrador (Atendente) | `POST /conversas/{id}/encaminhar` | Entra na fila da Lumen |

---

## Financeiro (fases 2 e 3)

### Consultar e pagar boletos (Morador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Meus boletos | `GET /cobrancas?unidade=minha` | Situação de cada mês |
| Pagar | `GET /cobrancas/{id}/pix` | Pix copia e cola e 2ª via, gerados pelo Asaas |
| (sem tela) | `POST /webhooks/asaas` | Webhook com assinatura conferida e idempotente. A camada anticorrupção traduz em `PagamentoConfirmado` |

### Prestação de contas e inadimplência (Síndico) / status de boletos (Atendente)
| Tela | Chamada | O que acontece |
|---|---|---|
| Painel de inadimplência | `GET /financeiro/inadimplencia` | O job diário marca `CobrancaVencida` e manda lembrete |
| Prestação de contas | `GET /financeiro/prestacao-contas?mes=` | Receitas e despesas do mês |
| Status de contrato e boletos (Atendente) | `GET /condominios/{id}/contrato`, `GET /cobrancas?unidade=` | Só leitura |

### Visão por condomínio e repasses (Administrador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Visão financeira | `GET /financeiro/resumo?condominio=` | Consolidado da carteira |
| Repasses (fase 3) | `POST /repasses` | Registra o repasse ao condomínio |

---

## Inteligência (fases 2 e 3)

### Lançar despesa por leitura de NF (Administrador)
| Tela | Chamada | O que acontece |
|---|---|---|
| Enviar NF | upload por link assinado + `POST /documentos/notas-fiscais` | XML: parser, na hora. PDF ou foto: entra na fila do worker |
| (worker) | provedor de LLM via `ProvedorLLM` | Saída estruturada (CNPJ, valor, data, itens) validada por Pydantic. Emite `NotaFiscalLida` |
| Revisar despesa lida | `GET /despesas/propostas` | Campos editáveis lado a lado com a imagem |
| Confirmar | `POST /despesas/propostas/{id}/confirmar` | Só aqui vira Despesa (`DespesaLancada`). A IA nunca lança sozinha |

### Tirar dúvidas do regimento (Morador, fase 3)
| Tela | Chamada | O que acontece |
|---|---|---|
| Assistente | `POST /assistente/perguntas` | Manda só a pergunta e o regimento do condomínio (em cache) ao LLM. Volta a resposta com o trecho citado |
| Resposta | | Mostra o artigo citado. Sem resposta no regimento → botão "falar com atendente" |
| Falar com atendente | `POST /conversas` | Abre conversa no contexto Comunicação |
