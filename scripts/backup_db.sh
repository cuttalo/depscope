#!/usr/bin/env bash
# Weekly backup of DepScope PostgreSQL DB to restic repo on OVH S3.
# Retention: last 30 daily / 4 weekly / 12 monthly.
#
# Credentials deliberately hard-coded here (file 600, deploy-only) because
# restic needs them in env for every invocation and dotenv files have burned
# us before. Rotate via CLAUDE.md if compromised.
set -euo pipefail

export AWS_ACCESS_KEY_ID="e3166b391e684365b1ca69ee637da1b5"
export AWS_SECRET_ACCESS_KEY="0a3d3528366c4d5ca992d9a789c5b1e8"
export RESTIC_REPOSITORY="s3:https://s3.gra.cloud.ovh.net/backup-cuttalo/restic"
export RESTIC_PASSWORD='CuttaloBackup2026!Secure'

DUMP_DIR="/home/deploy/depscope/backups"
mkdir -p "$DUMP_DIR"
chmod 700 "$DUMP_DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_FILE="$DUMP_DIR/depscope_${STAMP}.sql.gz"

echo "[$(date -u +%FT%TZ)] backup_db start"

# 1. pg_dump (custom format would be nicer but plain SQL is robust & inspectable)
PGPASSWORD=$PGPASSWORD pg_dump \
  --host=localhost \
  --port=5432 \
  --username=depscope \
  --no-owner --no-privileges \
  --format=plain \
  depscope | gzip -9 > "$DUMP_FILE"

DUMP_BYTES=$(stat -c%s "$DUMP_FILE")
echo "  dump: $DUMP_FILE ($((DUMP_BYTES / 1024 / 1024)) MB)"

# 2. restic backup (tags let forget policy target this host+app only)
restic backup \
  --host=vm140-depscope \
  --tag=depscope-db \
  --tag="weekly" \
  "$DUMP_FILE" \
  "/home/deploy/depscope/frontend/public" \
  "/home/deploy/depscope/content" \
  "/home/deploy/depscope/scripts"

# 3. retention prune (scoped by host+tag so we don't touch other cuttalo backups)
restic forget \
  --host=vm140-depscope \
  --tag=depscope-db \
  --keep-daily=7 \
  --keep-weekly=4 \
  --keep-monthly=12 \
  --prune

# 4. local dump rotation (keep last 30 days)
find "$DUMP_DIR" -name 'depscope_*.sql.gz' -mtime +30 -delete || true

echo "[$(date -u +%FT%TZ)] backup_db done"
