#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SQL_FILE="$ROOT/sql/bootstrap/create_arbitrage_user.sql"

if ! command -v psql >/dev/null 2>&1; then
    echo "psql not found. Install PostgreSQL client tools first." >&2
    exit 1
fi

# Prefer explicit superuser; fall back to current macOS user (Homebrew peer auth).
PG_SUPERUSER="${PG_SUPERUSER:-${USER:-postgres}}"

echo "Creating/updating Postgres role 'arbitrage' (password: arbitrage) as superuser '$PG_SUPERUSER'..."
psql -U "$PG_SUPERUSER" -d postgres -v ON_ERROR_STOP=1 -f "$SQL_FILE"

echo "Verifying connection with arbitrage/arbitrage..."
psql "postgresql://arbitrage:arbitrage@localhost:5432/arbitrage" -v ON_ERROR_STOP=1 -c "SELECT current_user, current_database();"

echo "Done. Use DATABASE_URL=postgresql://arbitrage:arbitrage@localhost:5432/arbitrage"
