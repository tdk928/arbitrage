from __future__ import annotations

"""Apply v3 market rules seed (total_goals_ou, both_teams_to_score)."""

from sqlalchemy.orm import sessionmaker

from scraper.db import get_engine, init_db
from scraper.v3.seed_rules import seed_all_rules


def main() -> None:
    init_db()
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        rules = seed_all_rules(session)
        session.commit()
        for rule in rules:
            print(f"Seeded rule: {rule.slug} (id={rule.id})")
            for sm in rule.site_matches:
                print(f"  - {sm.bookmaker_slug}: {sm.ui_label}")


if __name__ == "__main__":
    main()
