"""Run v3 rule-based scrape and persist odds to Postgres."""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy.orm import sessionmaker

from scraper.db import get_engine, init_db
from scraper.world_cup_v3 import run_world_cup_pipeline_v3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V3 scrape → Postgres (active market rules)")
    parser.add_argument("--competition", default="world-cup-2026", help=argparse.SUPPRESS)
    parser.add_argument(
        "--rules",
        nargs="*",
        help="Rule slugs to scrape (default: all active rules)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    init_db()
    Session = sessionmaker(bind=get_engine())
    session = Session()
    try:
        result = run_world_cup_pipeline_v3(
            session,
            triggered_by="cli",
            rule_slugs=args.rules or None,
        )
    finally:
        session.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"run_id={result['run_id']} status={result['status']}")
        print(f"stats: {json.dumps(result['stats'], ensure_ascii=False)}")
        if result.get("errors"):
            print(f"errors: {result['errors'][:500]}")
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
