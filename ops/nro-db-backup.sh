#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/apps/Ngoc-Rong-For-Study"
BACKUP_DIR="/var/backups/game-nro"

cd "$APP_DIR"
install -d -o root -g root -m 700 "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%d-%H%M%S)"
backup_file="$BACKUP_DIR/ngocrong-$timestamp.sql"
temp_file="$(mktemp "$BACKUP_DIR/.ngocrong-$timestamp.XXXXXX")"
trap 'rm -f -- "$temp_file"' EXIT

docker compose exec -T db sh -c \
  'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction "$MARIADB_DATABASE"' \
  > "$temp_file"

test -s "$temp_file"
chmod 600 "$temp_file"
mv -- "$temp_file" "$backup_file"
trap - EXIT

printf 'Database backup created: %s\n' "$backup_file"
