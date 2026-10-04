#!/usr/bin/env bash
# Prova que um backup restaura: cria um banco temporario, restaura e conta as linhas das tabelas.
# Backup que nunca foi restaurado nao e backup; rode isto de tempos em tempos.
#
#   uso: RESTORE_ADMIN_URL=postgresql://postgres:senha@localhost:5432/postgres \
#        ./restore-test.sh lumen-20261004-030000.dump
#
# RESTORE_ADMIN_URL aponta para um Postgres de teste (nunca o de producao): o script cria e apaga
# o banco lumen_restore_test nele.
set -euo pipefail

arquivo="${1:?uso: restore-test.sh <arquivo.dump>}"
: "${RESTORE_ADMIN_URL:?defina RESTORE_ADMIN_URL (Postgres de teste, nao o de producao)}"
banco=lumen_restore_test
# troca o nome do banco no fim da URL (antes de eventual ?query)
url_teste="$(sed -E "s#/[^/?]*(\?|$)#/$banco\1#" <<< "$RESTORE_ADMIN_URL")"

psql "$RESTORE_ADMIN_URL" -qc "DROP DATABASE IF EXISTS $banco"
psql "$RESTORE_ADMIN_URL" -qc "CREATE DATABASE $banco"
trap 'psql "$RESTORE_ADMIN_URL" -qc "DROP DATABASE IF EXISTS $banco"' EXIT

pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error --dbname="$url_teste" "$arquivo"

tabelas="$(psql "$url_teste" -Atc "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")"
if [[ -z "$tabelas" ]]; then
  echo "restauracao falhou: nenhuma tabela em public" >&2
  exit 1
fi
for t in $tabelas; do
  echo "$t: $(psql "$url_teste" -Atc "SELECT count(*) FROM public.\"$t\"")"
done
echo "restauracao ok"
