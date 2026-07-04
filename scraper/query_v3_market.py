"""Read v3 market odds from Postgres (no live scrape)."""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy.orm import sessionmaker

from scraper.db import get_engine, init_db
from scraper.v3.query import fetch_market_odds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query v3 odds from DB")
    parser.add_argument("rule_slug", help="e.g. total_goals_ou")
    parser.add_argument("--home", required=True, help="Home team substring (e.g. Canada, Канада)")
    parser.add_argument("--away", required=True, help="Away team substring (e.g. Morocco, Мароко)")
    parser.add_argument("--run-id", type=int, help="Scrape run id (default: latest success/partial)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    init_db()
    Session = sessionmaker(bind=get_engine())
    session = Session()
    try:
        data = fetch_market_odds(
            session,
            rule_slug=args.rule_slug,
            home_terms=(args.home,),
            away_terms=(args.away,),
            run_id=args.run_id,
        )
    finally:
        session.close()

    if not data:
        print("No data found.", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"Rule: {data['rule']} (run_id={data['run_id']})")
    print(f"Match: {data['home']} vs {data['away']} ({data['kickoff_utc']})")
    print()
    for slug, site in data["sites"].items():
        print(f"=== {slug} ({site.get('ui_label', '?')}) ===")
        if not site.get("lines"):
            print("  (no lines)")
            print()
            continue
        print(f"  event_id: {site.get('event_id')}")
        print(f"  {'Line':>5}  {'Over':>6}  {'Under':>6}")
        for row in site["lines"]:
            print(f"  {row['line']:>5}  {row['over']:>6}  {row['under']:>6}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
