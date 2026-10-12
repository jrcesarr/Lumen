# 0009. Backup do banco por pg_dump no Object Storage

**Contexto.** O Supabase Free nao guarda backups que possamos baixar (o plano Pro tem). O custo da fase 1 e zero (ver `docs/arquitetura.md`), mas perder o banco acabaria o projeto.

**Decisao.** Um script (`infra/backup/backup.sh`) roda todo dia na VM, copia os schemas `public` e `auth` com `pg_dump` e envia ao Object Storage gratuito da Oracle. Ficam 14 diarios e 4 semanais, no bucket privado `lumen-backup` (ver [0011](0011-object-storage-da-oracle.md)). `infra/backup/restore-test.sh` restaura um dump num Postgres de teste e conta as linhas; o CI roda os dois contra um banco com as migrations.

**Consequencias.** Custo zero, mas o pior caso e perder ate 24 h de dados. O backup so vale se a restauracao for testada: o teste manual contra o banco real do Supabase fica como tarefa de operacao (ver `docs/backup.md`). Ao passar para o Pro, os backups gerenciados entram e este script continua como copia fora do Supabase. Os dumps e os arquivos dos usuarios ficam na mesma conta Oracle; uma copia semanal para outro provedor (rclone para o Cloudflare R2) e o proximo passo.
