#!/usr/bin/env bash
# Build (or rebuild) db/view-bot.sqlite from db/schema.sql and db/seed.sql, then run
# the sanity checks in scripts/verify-seed.sql.
#
#   scripts/build-db.sh           # refuses to overwrite an existing database
#   scripts/build-db.sh --reset   # deletes the existing database first
#
# Needs the sqlite3 command line tool (preinstalled on macOS; `apt install sqlite3` on Debian/Ubuntu).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
db="$root/db/view-bot.sqlite"

command -v sqlite3 >/dev/null || { echo "sqlite3 not found" >&2; exit 1; }

if [ -f "$db" ]; then
  if [ "${1:-}" = "--reset" ]; then
    rm -f "$db" "$db-journal" "$db-wal" "$db-shm"
  else
    echo "$db already exists; pass --reset to rebuild it from scratch" >&2
    exit 1
  fi
fi

sqlite3 "$db" < "$root/db/schema.sql"
sqlite3 "$db" < "$root/db/seed.sql"
echo "built $db"
sqlite3 "$db" < "$root/scripts/verify-seed.sql"
