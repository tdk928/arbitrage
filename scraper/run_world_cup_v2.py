from __future__ import annotations

"""CLI entry point for v2 all-markets World Cup pipeline."""

import argparse
import json

from sqlalchemy.orm import sessionmaker

from scraper.db import get_engine, init_db
from scraper.db_init_v2 import init_db_v2
from scraper.seed import seed_session
from scraper.world_cup_v2 import run_world_cup_pipeline_v2


def main() -> None:
    parser = argparse.ArgumentParser(
        description="V2: scrape ALL markets from efbet/winbet/inbet/palmsbet and find arbitrage"
    )
    parser.add_argument("--min-margin", type=float, default=1.0, help="Min margin %% (default 1)")
    parser.add_argument("--limit", type=int, default=10, help="Top N opportunities in output")
    parser.add_argument("--seed", action="store_true", help="Re-seed DB config before scrape")
    args = parser.parse_args()

    init_db()
    init_db_v2()
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        if args.seed:
            seed_session(session)
        result = run_world_cup_pipeline_v2(
            session,
            min_margin=args.min_margin,
            limit=args.limit,
            triggered_by="cli",
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
