#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DATABASE_URL="${DATABASE_URL:-postgresql://arbitrage:arbitrage@localhost:5432/arbitrage}"

# Ensure local dev role exists (arbitrage/arbitrage). Safe to re-run.
"$ROOT/scripts/setup_postgres_user.sh"

cd "$ROOT"
python -m scraper.migrate
python -m scraper.seed
python -m scraper.seed_market_rules
