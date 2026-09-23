#!/usr/bin/env bash
set -euo pipefail
: "${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL is required}"
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required and must target an isolated database}"
backup="${1:-querysmith-backup.dump}"
pg_dump --format=custom --no-owner --dbname="$SOURCE_DATABASE_URL" --file="$backup"
pg_restore --clean --if-exists --no-owner --dbname="$RESTORE_DATABASE_URL" "$backup"
psql "$RESTORE_DATABASE_URL" -v ON_ERROR_STOP=1 -c 'SELECT count(*) FROM alembic_version;'
echo "Backup restore verification completed against the isolated target."
