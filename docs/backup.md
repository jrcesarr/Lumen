# Backup do banco

O Supabase Free nao guarda backups (o Pro guarda), entao o backup e nosso. Decisao em [0009](decisoes/0009-backup-por-pg-dump.md).

## O que roda

`infra/backup/backup.sh`, uma vez por dia na VM:

1. `pg_dump` em formato custom dos schemas `public` (dados) e `auth` (logins), mais a extensao `btree_gist`.
2. Confere que o arquivo e legivel (`pg_restore --list`). Se falhar, nada e enviado e o script sai com erro.
3. Envia para `diario/` no destino; aos domingos copia tambem para `semanal/`.
4. Apaga diarios com mais de 7 dias e semanais com mais de 28.

| Variavel | Para que serve |
|---|---|
| `BACKUP_DATABASE_URL` | conexao do Postgres do Supabase |
| `BACKUP_DESTINO` | pasta local, ou remote do rclone (ex.: `oci:lumen-backups`) |
| `BACKUP_SCHEMAS`, `BACKUP_EXTENSOES` | o que copiar (padrao `public auth` e `btree_gist`) |
| `BACKUP_DIAS_DIARIOS`, `BACKUP_DIAS_SEMANAIS` | retencao (padrao 7 e 28) |

## Na VM

```bash
# cron do usuario que roda o Docker Compose, todo dia as 03:00 UTC
0 3 * * * BACKUP_DATABASE_URL=... BACKUP_DESTINO=oci:lumen-backups /opt/lumen/infra/backup/backup.sh >> /var/log/lumen-backup.log 2>&1
```

- Precisa de `pg_dump` na versao do Supabase (ou mais nova) e do `rclone`.
- O Object Storage da Oracle tem API compativel com S3: configure o remote do rclone como S3 com o endpoint do seu namespace e regiao (confira o formato na documentacao da Oracle).
- A conexao direta do Supabase pode ser so IPv6. Se a VM nao tiver IPv6, use a string do pooler em modo sessao. **Confirme no painel antes de depender disso.**
- Alerta: se o log nao tiver "backup ok" no dia, algo falhou.

## Restaurar (e provar que funciona)

```bash
RESTORE_ADMIN_URL=postgresql://postgres:senha@localhost:5432/postgres \
  infra/backup/restore-test.sh lumen-20261004-030000.dump
```

Cria o banco `lumen_restore_test` num Postgres de teste, restaura, lista as tabelas com a contagem de linhas e apaga o banco. Nunca aponte para o banco de producao. O CI faz isso a cada PR com um banco de teste.

**Ainda por fazer (operacao):** rodar o `restore-test.sh` com um dump real do Supabase. O CI simula o schema `auth`, e o dump do Supabase pode trazer objetos proprios dele (roles e extensoes no schema `extensions`) que exijam ajuste.
