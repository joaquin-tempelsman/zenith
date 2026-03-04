#!/usr/bin/env bash
# ════════════════════════════════════════════════════════
#  💾 Daily SQLite Backup Script
# ════════════════════════════════════════════════════════
#
# Creates consistent snapshots of ALL SQLite databases
# (per-user inventory DBs + shared metadata.db) using
# sqlite3 .backup for crash-safe copies.
#
# Usage:
#   ./scripts/backup-databases.sh              # defaults: /app/data -> /opt/backups/zenith
#   ./scripts/backup-databases.sh /path/to/data /path/to/backups
#
# Retention: keeps the last 30 days of backups.
# Intended to be run via cron (see deploy/setup-new-droplet.sh).

set -euo pipefail

DATA_DIR="${1:-/app/data}"
BACKUP_ROOT="${2:-/opt/backups/zenith}"
RETENTION_DAYS=30
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

# ── Preflight checks ────────────────────────────────────

if ! command -v sqlite3 &>/dev/null; then
    echo "[$(date)] ERROR: sqlite3 not found. Install it first." >&2
    exit 1
fi

if [ ! -d "$DATA_DIR" ]; then
    echo "[$(date)] ERROR: Data directory '$DATA_DIR' does not exist." >&2
    exit 1
fi

DB_COUNT=$(find "$DATA_DIR" -maxdepth 1 -name "*.db" 2>/dev/null | wc -l)
if [ "$DB_COUNT" -eq 0 ]; then
    echo "[$(date)] WARNING: No .db files found in '$DATA_DIR'. Nothing to back up."
    exit 0
fi

# ── Create backup ────────────────────────────────────────

mkdir -p "$BACKUP_DIR"

BACKED_UP=0
FAILED=0

for db_file in "$DATA_DIR"/*.db; do
    [ -f "$db_file" ] || continue
    filename="$(basename "$db_file")"
    if sqlite3 "$db_file" ".backup '$BACKUP_DIR/$filename'" 2>/dev/null; then
        BACKED_UP=$((BACKED_UP + 1))
    else
        echo "[$(date)] WARNING: Failed to backup $filename" >&2
        FAILED=$((FAILED + 1))
    fi
done

# ── Compress ─────────────────────────────────────────────

tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_ROOT" "$TIMESTAMP"
rm -rf "$BACKUP_DIR"

# ── Retention cleanup ────────────────────────────────────

find "$BACKUP_ROOT" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# ── Summary ──────────────────────────────────────────────

ARCHIVE_SIZE=$(du -h "$BACKUP_DIR.tar.gz" | cut -f1)
echo "[$(date)] Backup complete: $BACKED_UP DBs backed up ($FAILED failed), archive: $BACKUP_DIR.tar.gz ($ARCHIVE_SIZE)"
