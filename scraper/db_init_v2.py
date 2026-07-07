"""Create v2 all-markets tables (parallel schema; v1 untouched)."""

from __future__ import annotations

from scraper.db import get_engine, init_db
from scraper.models import Base

# Import v2 models so they register on shared Base.metadata
import scraper.models_v2  # noqa: F401

V2_TABLES = {
    "scrape_runs_v2",
    "canonical_markets_v2",
    "raw_markets_v2",
    "odds_snapshots_v2",
    "arbitrage_opportunities_v2",
}


def init_db_v2() -> None:
    init_db()
    tables = [t for name, t in Base.metadata.tables.items() if name in V2_TABLES]
    Base.metadata.create_all(bind=get_engine(), tables=tables)


def main() -> None:
    init_db_v2()
    print("V2 database tables created (or already exist).")


if __name__ == "__main__":
    main()
