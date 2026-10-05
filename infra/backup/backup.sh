#!/usr/bin/env bash
# Backup diario do banco. O Supabase Free nao guarda backups, entao este script faz o papel.
#
#   BACKUP_DATABASE_URL  string de conexao do Postgres do Supabase (obrigatoria)
#   BACKUP_DESTINO       pasta local ou remote do rclone, ex.: oci:lumen-backups (obrigatoria)
#   BACKUP_SCHEMAS       schemas copiados (padrao: "public auth"; o auth guarda os logins)
#   BACKUP_EXTENSOES     extensoes que o schema usa (padrao: btree_gist, da exclusion constraint das reservas)
#   BACKUP_DIAS_DIARIOS  quantos dias guardar os diarios (padrao: 7)
#   BACKUP_DIAS_SEMANAIS quantos dias guardar os semanais, copiados aos domingos (padrao: 28)
set -euo pipefail

: "${BACKUP_DATABASE_URL:?defina BACKUP_DATABASE_URL}"
: "${BACKUP_DESTINO:?defina BACKUP_DESTINO (pasta local ou remote do rclone)}"
schemas="${BACKUP_SCHEMAS:-public auth}"
extensoes="${BACKUP_EXTENSOES:-btree_gist}"
dias_diarios="${BACKUP_DIAS_DIARIOS:-7}"
dias_semanais="${BACKUP_DIAS_SEMANAIS:-28}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
nome="lumen-$(date -u +%Y%m%d-%H%M%S).dump"
arquivo="$tmp/$nome"

args=()
for s in $schemas; do args+=("--schema=$s"); done
for e in $extensoes; do args+=("--extension=$e"); done
pg_dump --format=custom --no-owner --no-privileges "${args[@]}" --file="$arquivo" "$BACKUP_DATABASE_URL"

# Se o arquivo nao for legivel, o envio nem acontece (e o cron avisa pelo codigo de saida).
pg_restore --list "$arquivo" > /dev/null

enviar() { # enviar <arquivo> <pasta no destino>
  if [[ "$BACKUP_DESTINO" == /* ]]; then
    mkdir -p "$BACKUP_DESTINO/$2"
    cp "$1" "$BACKUP_DESTINO/$2/"
  else
    rclone copy "$1" "$BACKUP_DESTINO/$2"
  fi
}

apagar_antigos() { # apagar_antigos <pasta no destino> <dias>
  if [[ "$BACKUP_DESTINO" == /* ]]; then
    [[ -d "$BACKUP_DESTINO/$1" ]] || return 0
    find "$BACKUP_DESTINO/$1" -name '*.dump' -mmin "+$(($2 * 1440))" -delete
  else
    rclone delete "$BACKUP_DESTINO/$1" --min-age "${2}d"
  fi
}

enviar "$arquivo" diario
if [[ "$(date -u +%u)" == 7 ]]; then enviar "$arquivo" semanal; fi
apagar_antigos diario "$dias_diarios"
apagar_antigos semanal "$dias_semanais"

echo "backup ok: $nome ($(du -h "$arquivo" | cut -f1))"
