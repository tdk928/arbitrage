"""Create all SQLAlchemy tables in the configured database."""

from __future__ import annotations

from scraper.db import init_db


def main() -> None:
    init_db()
    print("Database tables created (or already exist).")


if __name__ == "__main__":
    main()
