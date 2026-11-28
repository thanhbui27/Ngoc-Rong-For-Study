#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/apps/Ngoc-Rong-For-Study"
cd "$APP_DIR"

skip_database_backup=false
if [[ ${1:-} == --skip-database-backup && $# == 1 ]]; then
  skip_database_backup=true
elif (( $# != 0 )); then
  echo "Usage: deploy.sh [--skip-database-backup]" >&2
  exit 1
fi

if ! "$skip_database_backup"; then
  echo "=== Backup database ==="
  sudo -n /usr/local/sbin/nro-db-backup
fi

echo "=== Pull latest code ==="
git fetch origin main
git merge --ff-only origin/main

echo "=== Build Login ==="
(cd Login && mvn clean package -DskipTests)

echo "=== Build Server ==="
(cd Server && mvn clean package -DskipTests)

echo "=== Copy JAR files ==="
shopt -s nullglob

login_jars=(Login/target/*-jar-with-dependencies.jar)
server_jars=(Server/target/*-jar-with-dependencies.jar)

if (( ${#login_jars[@]} != 1 || ${#server_jars[@]} != 1 )); then
  echo "ERROR: Expected exactly one JAR per module"
  exit 1
fi

echo "=== Apply pending database migrations ==="
if "$skip_database_backup"; then
  # This path is for an already backed-up, migrated DB and never invokes Docker.
  migration_status=$(java -cp "${server_jars[0]}" nro.db.MigrationRunner --dry-run)
  printf '%s\n' "$migration_status"
  if grep -q '^Pending ' <<< "$migration_status"; then
    echo "ERROR: Cannot skip the database backup while migrations are pending" >&2
    exit 1
  fi
else
  java -cp "${server_jars[0]}" nro.db.MigrationRunner --apply
fi

cp "${login_jars[0]}" Login/Login.jar
cp "${server_jars[0]}" Server/Server.jar

echo "=== Restart services ==="
sudo systemctl restart nro-login
sudo systemctl restart nro-server

echo "=== Deploy complete ==="
