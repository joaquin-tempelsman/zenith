#!/usr/bin/env bash
# ════════════════════════════════════════════════════════
#  🔄 Run Alembic Migrations on All Databases
# ════════════════════════════════════════════════════════
#
# Applies pending Alembic migrations to every per-user
# inventory database found in the data directory.
#
# Usage:
#   ./scripts/run-migrations.sh                 # upgrade to head
#   ./scripts/run-migrations.sh downgrade -1    # rollback one revision

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

ACTION="${1:-upgrade}"
TARGET="${2:-head}"

echo "════════════════════════════════════════════════════════"
echo "  🔄 Running Alembic Migrations: $ACTION $TARGET"
echo "════════════════════════════════════════════════════════"
echo ""

uv run alembic "$ACTION" "$TARGET"

echo ""
echo "✅ Migrations complete!"
