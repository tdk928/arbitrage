from __future__ import annotations

"""Seed bookmakers, market types, World Cup 2026 competition sources."""

from sqlalchemy.orm import Session

from scraper.db import get_engine, init_db
from scraper.models import Bookmaker, Competition, CompetitionSource, MarketType
from scraper.world_cup import WC_EGT_SEARCH_TERMS
from sqlalchemy.orm import sessionmaker

MARKET_TYPES = [
    ("MATCH_1X2", "Match Result 1X2", 3, None),
    ("GOALS_OU_25", "Goals Over/Under 2.5", 2, "2.5"),
    ("CORNERS_OU_85", "Corners Over/Under 8.5", 2, "8.5"),
    ("CORNERS_OU_95", "Corners Over/Under 9.5", 2, "9.5"),
]

BOOKMAKERS = [
    ("bet365", "Bet365", "bet365"),
    ("winbet", "Winbet", "egt"),
    ("inbet", "Inbet", "egt"),
    ("palmsbet", "Palmsbet", "altenar"),
    ("8888", "8888", "sportinno"),
    ("efbet", "Efbet", "efbet"),
]


def seed_session(session: Session) -> None:
    for code, name, outcome_count, line in MARKET_TYPES:
        if not session.query(MarketType).filter(MarketType.code == code).one_or_none():
            session.add(
                MarketType(
                    code=code,
                    name=name,
                    outcome_count=outcome_count,
                    line=line,
                )
            )

    bm_ids: dict[str, int] = {}
    for slug, name, platform in BOOKMAKERS:
        bm = session.query(Bookmaker).filter(Bookmaker.slug == slug).one_or_none()
        if not bm:
            bm = Bookmaker(slug=slug, name=name, platform=platform)
            session.add(bm)
            session.flush()
        bm_ids[slug] = bm.id

    comp = session.query(Competition).filter(Competition.slug == "world-cup-2026").one_or_none()
    if not comp:
        comp = Competition(
            slug="world-cup-2026",
            name="FIFA World Cup 2026",
            sport="football",
            season="2026",
        )
        session.add(comp)
        session.flush()

    sources = [
        (
            "efbet",
            "api_tab",
            {
                "tab_id": 59354,
                "tournament_id": 1701,
            },
            "https://efbet.com/sport/soccer-120/national-teams-1204/world-cup-1701",
        ),
        (
            "winbet",
            "api_tournament",
            {
                "tournament_name": "Световно Първенство",
                "search_terms": WC_EGT_SEARCH_TERMS,
            },
            "https://www.winbet.bg/sport",
        ),
        (
            "inbet",
            "api_tournament",
            {
                "tournament_name": "Световно Първенство",
                "search_terms": WC_EGT_SEARCH_TERMS,
            },
            "https://www.inbet.bg/sport",
        ),
        (
            "palmsbet",
            "api_tournament",
            {"sport_id": 66, "champ_id": 3146, "endpoint": "GetEvents"},
            "https://www.palmsbet.com/bg/sport",
        ),
        (
            "8888",
            "api_tournament",
            {
                "tournament_id": 56878,
                "bid": "1294778290",
                "altenar_fallback": {
                    "integration": "8888.bg",
                    "sport_id": 66,
                    "champ_id": 3146,
                    "endpoint": "GetEvents",
                },
            },
            "https://8888.bg/sport/",
        ),
        (
            "bet365",
            "html_list",
            {
                "hub_url": "https://www.bet365.com/hub/en-gb/football/football-competitions/world-cup"
            },
            "https://www.bet365.com/hub/en-gb/football/football-competitions/world-cup",
        ),
    ]

    for slug, dtype, config, url in sources:
        exists = (
            session.query(CompetitionSource)
            .filter(
                CompetitionSource.competition_id == comp.id,
                CompetitionSource.bookmaker_id == bm_ids[slug],
            )
            .one_or_none()
        )
        if exists:
            exists.discovery_type = dtype
            exists.discovery_config = config
            exists.listing_url = url
        else:
            session.add(
                CompetitionSource(
                    competition_id=comp.id,
                    bookmaker_id=bm_ids[slug],
                    discovery_type=dtype,
                    discovery_config=config,
                    listing_url=url,
                )
            )

    session.commit()


def main() -> None:
    init_db()
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    with Session() as session:
        seed_session(session)
    print("Seed completed.")


if __name__ == "__main__":
    main()
