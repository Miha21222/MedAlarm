#!/usr/bin/env sh
set -eu

backup_dir="${BACKUP_DIR:-/var/backups/medalarm}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_id="$(docker compose ps -q backend)"
[ -n "$container_id" ] || { echo "Backend container is not running" >&2; exit 1; }

mkdir -p "$backup_dir/daily" "$backup_dir/weekly"
tmp_name="medalarm-$timestamp.db"
docker compose exec -T backend python -c \
  "import sqlite3; source=sqlite3.connect('/app/data/medalarm.db'); target=sqlite3.connect('/app/data/$tmp_name'); source.backup(target); target.close(); source.close()"
docker cp "$container_id:/app/data/$tmp_name" "$backup_dir/daily/$tmp_name"
docker compose exec -T backend rm -f "/app/data/$tmp_name"
gzip "$backup_dir/daily/$tmp_name"
chmod 600 "$backup_dir/daily/$tmp_name.gz"
gzip -t "$backup_dir/daily/$tmp_name.gz"

find "$backup_dir/daily" -type f -name 'medalarm-*.db.gz' -mtime +7 -delete
if [ "$(date -u +%u)" = "7" ]; then
  cp "$backup_dir/daily/$tmp_name.gz" "$backup_dir/weekly/$tmp_name.gz"
  find "$backup_dir/weekly" -type f -name 'medalarm-*.db.gz' -mtime +28 -delete
fi
echo "$backup_dir/daily/$tmp_name.gz"
