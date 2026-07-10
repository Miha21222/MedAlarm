#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "Usage: $0 <medalarm-backup.db.gz>" >&2
  exit 2
fi

backup_file="$(realpath "$1")"
gzip -t "$backup_file"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
gzip -dc "$backup_file" > "$tmp_dir/medalarm.db"
python3 - "$tmp_dir/medalarm.db" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
result = connection.execute("PRAGMA integrity_check").fetchone()[0]
connection.close()
if result != "ok":
    raise SystemExit(f"Backup integrity check failed: {result}")
PY

docker compose --profile production down
docker compose run --rm --no-deps -v "$tmp_dir:/restore:ro" backend python -c \
  "import shutil; shutil.copyfile('/restore/medalarm.db', '/app/data/medalarm.db')"
docker compose --profile production up -d
echo "Restored $backup_file"
