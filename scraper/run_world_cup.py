from __future__ import annotations

"""Scrape all World Cup 2026 fixtures from 6 bookmakers and compute arbitrage."""

import argparse
import json

from sqlalchemy.orm import sessionmaker

from scraper.db import get_engine, init_db
from scraper.seed import seed_session
from scraper.world_cup import run_world_cup_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape all World Cup 2026 matches from 6 bookmakers and find arbitrage"
    )
    parser.add_argument("--min-margin", type=float, default=1.0, help="Min margin %% (default 1)")
    parser.add_argument("--limit", type=int, default=10, help="Top N opportunities in output")
    parser.add_argument("--seed", action="store_true", help="Re-seed DB config before scrape")
    args = parser.parse_args()

    init_db()
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        if args.seed:
            seed_session(session)
        result = run_world_cup_pipeline(
            session,
            min_margin=args.min_margin,
            limit=args.limit,
            triggered_by="cli",
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
