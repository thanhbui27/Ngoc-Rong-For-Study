#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/apps/Ngoc-Rong-For-Study"
cd "$APP_DIR"

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
java -cp "${server_jars[0]}" nro.db.MigrationRunner --apply

cp "${login_jars[0]}" Login/Login.jar
cp "${server_jars[0]}" Server/Server.jar

echo "=== Restart services ==="
sudo systemctl restart nro-login
sudo systemctl restart nro-server

echo "=== Deploy complete ==="
