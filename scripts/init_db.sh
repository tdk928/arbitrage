#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DATABASE_URL="${DATABASE_URL:-postgresql://arbitrage:arbitrage@localhost:5432/arbitrage}"
cd "$ROOT"
python -m scraper.seed
