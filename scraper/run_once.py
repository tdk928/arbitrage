from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy.orm import sessionmaker

from scraper.db import get_engine, init_db
from scraper.pipeline import run_pipeline
from scraper.seed import seed_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Run arbitrage scrape once")
    parser.add_argument("--competition", default="world-cup-2026")
    parser.add_argument(
        "--time-window",
        default="today_tomorrow",
        choices=["next_24h", "today_tomorrow", "all"],
        help="'all' = no time filter (useful for World Cup full fixture list)",
    )
    parser.add_argument("--min-margin", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--budget", type=float, default=100.0, help="Stake budget in EUR")
    parser.add_argument("--seed", action="store_true", help="Run DB seed before scrape")
    args = parser.parse_args()

    init_db()
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        if args.seed:
            seed_session(session)
        result = run_pipeline(
            session,
            competition_slug=args.competition,
            time_window=args.time_window,
            min_margin=args.min_margin,
            limit=args.limit,
            budget_eur=args.budget,
            triggered_by="cli",
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
