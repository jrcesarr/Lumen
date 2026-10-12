# 0011. Arquivos no Oracle Object Storage, nao no MinIO

**Contexto.** O plano inicial guardava fotos de chamados, notas fiscais e regimentos num MinIO rodando na mesma VM. A edicao comunitaria do MinIO entrou em modo de manutencao em 2025, passou a sair so como codigo-fonte e o repositorio foi arquivado em 2026: nao recebe mais correcoes de seguranca. Para um sistema que guarda documentos de moradores (LGPD), depender disso e um risco que nao precisamos correr. Alem disso, o MinIO ocupa o disco da VM e exige que alguem o mantenha.

**Decisao.** Em producao os arquivos ficam no **Oracle Object Storage**, na mesma conta e regiao (Sao Paulo) da VM:

- `lumen-arquivos`: privado, com versionamento ligado. Fotos, notas fiscais e regimentos.
- `lumen-backup`: privado. Os dumps do `backup.sh` (ver [0009](0009-backup-por-pg-dump.md)).
- O codigo fala **S3** (API compativel do Object Storage, acessada com Customer Secret Keys). O provedor e so configuracao: endpoint, regiao, chave e bucket vem de variaveis de ambiente (`STORAGE_ENDPOINT`, `STORAGE_REGION`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET_ARQUIVOS`). Trocar de provedor nao muda codigo.
- O navegador envia e baixa direto do bucket por **link assinado** que expira em minutos; a API so autoriza (permissao e condominio) e gera o link, entao a regra "todo dado passa pela API" continua valendo.
- No desenvolvimento, o `docker-compose.yml` sobe um S3 local (`s3-dev`). Hoje e uma imagem do MinIO **fixa numa versao e so para dev**; ao entrar a primeira funcionalidade de arquivos, ela deve ser trocada por um S3 mantido (Garage ou SeaweedFS).

**Por que Object Storage e nao outras opcoes.**

| Opcao | Por que nao |
|---|---|
| MinIO na VM | Sem correcoes de seguranca, consome o disco da VM, exige manutencao |
| Disco da VM | Se a VM se perder, os arquivos vao junto; sem link assinado nem versionamento |
| Supabase Storage | Acessa o banco por fora da API e duplicaria a regra de acesso |
| Object Storage da Oracle | Mantido pelo provedor, fala S3, 20 GB no Always Free, nao ocupa disco da VM e nao exige manutencao |

**Consequencias.** Custo continua zero na fase 1 (20 GB cobrem o inicio; depois paga-se por GB, centavos). Os arquivos sao protegidos pelo versionamento do bucket, sem `mc mirror`. O ponto fraco e que arquivos e dumps ficam na **mesma conta Oracle**: se a conta for suspensa, perde-se tudo. O proximo passo e uma copia semanal com rclone para o Cloudflare R2. As chaves S3 nunca vao para o repositorio. Nenhuma funcionalidade grava arquivo ainda; esta decisao fixa o destino antes de o codigo existir.
