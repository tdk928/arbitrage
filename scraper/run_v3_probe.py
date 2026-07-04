"""Probe v3 rule matching: scrape one match and print matched total_goals_ou lines."""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy.orm import sessionmaker

from scraper.db import get_engine, init_db
from scraper.models import Bookmaker, Competition, CompetitionSource
from scraper.models_v3 import MarketRuleSet, MarketRuleSiteMatch
from scraper.platforms.registry import get_scraper
from scraper.time_filter import filter_fixtures
from scraper.v2.raw_fetchers import fetch_all_markets_for_event
from scraper.v3.criteria import criteria_match
from scraper.v3.seed_rules import TOTAL_GOALS_OU_SLUG

V3_BOOKMAKERS = ("efbet", "winbet", "inbet", "palmsbet", "8888")

# Reference WC match for calibration verification
DEFAULT_MATCH_TERMS = ("mexico", "mex", "англ", "england", "engl")


def _find_fixture(session, competition_slug: str, terms: tuple[str, ...]):
    comp = session.query(Competition).filter(Competition.slug == competition_slug).one()
    sources = {
        src.bookmaker_id: src
        for src in session.query(CompetitionSource)
        .filter(CompetitionSource.competition_id == comp.id)
        .all()
    }
    found: dict[str, tuple] = {}
    for slug in V3_BOOKMAKERS:
        bm = session.query(Bookmaker).filter(Bookmaker.slug == slug).one()
        src = sources[bm.id]
        cfg = src.discovery_config or {}
        fixtures = filter_fixtures(get_scraper(slug).list_fixtures(cfg), "world_cup")
        for fx in fixtures:
            text = f"{fx.home_team} {fx.away_team}".lower()
            if any(t in text for t in terms):
                found[slug] = (fx, bm.platform, cfg)
                break
    return found


def _market_row(market) -> dict:
    return {
        "line": market.line,
        "market_name": market.market_name,
        "over": next((o.odd for o in market.outcomes if o.role == "over"), None),
        "under": next((o.odd for o in market.outcomes if o.role == "under"), None),
    }


def run_probe(competition_slug: str = "world-cup-2026") -> dict:
    init_db()
    Session = sessionmaker(bind=get_engine())
    session = Session()

    rule = (
        session.query(MarketRuleSet)
        .filter(MarketRuleSet.slug == TOTAL_GOALS_OU_SLUG)
        .one()
    )
    site_rules = {
        sm.bookmaker_slug: sm
        for sm in session.query(MarketRuleSiteMatch)
        .filter(MarketRuleSiteMatch.rule_set_id == rule.id, MarketRuleSiteMatch.is_active.is_(True))
        .all()
    }

    fixtures = _find_fixture(session, competition_slug, DEFAULT_MATCH_TERMS)
    if not fixtures:
        session.close()
        raise RuntimeError("No fixtures found for probe match")

    # Pick display name from efbet or first available
    ref_fx = fixtures.get("efbet", next(iter(fixtures.values())))[0]
    result: dict = {
        "rule": rule.slug,
        "match": f"{ref_fx.home_team} vs {ref_fx.away_team}",
        "kickoff_utc": ref_fx.kickoff_utc.isoformat(),
        "sites": {},
    }

    for slug in V3_BOOKMAKERS:
        if slug not in fixtures:
            result["sites"][slug] = {"status": "fixture_not_found", "lines": []}
            continue
        fx, platform, cfg = fixtures[slug]
        sm = site_rules.get(slug)
        if not sm:
            result["sites"][slug] = {"status": "no_rule", "lines": []}
            continue
        try:
            all_markets = fetch_all_markets_for_event(slug, platform, fx.external_id, cfg)
            matched = [m for m in all_markets if criteria_match(sm.match_criteria, m)]
            matched.sort(key=lambda m: float(m.line or 0))
            result["sites"][slug] = {
                "status": "ok",
                "ui_label": sm.ui_label,
                "event_id": fx.external_id,
                "total_markets_scraped": len(all_markets),
                "matched_lines": len(matched),
                "lines": [_market_row(m) for m in matched],
            }
        except Exception as exc:
            result["sites"][slug] = {"status": "error", "error": str(exc), "lines": []}

    session.close()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe v3 total_goals_ou scraping")
    parser.add_argument("--competition", default="world-cup-2026")
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    args = parser.parse_args(argv)

    data = run_probe(args.competition)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"Rule: {data['rule']}")
    print(f"Match: {data['match']} ({data['kickoff_utc']})")
    print()
    for slug, site in data["sites"].items():
        print(f"=== {slug} ({site.get('ui_label', '?')}) ===")
        if site["status"] != "ok":
            print(f"  status: {site['status']}", site.get("error", ""))
            print()
            continue
        print(f"  event_id: {site['event_id']}")
        print(f"  scraped: {site['total_markets_scraped']} markets → matched: {site['matched_lines']} lines")
        print(f"  {'Line':>5}  {'Over':>6}  {'Under':>6}")
        for row in site["lines"]:
            print(f"  {row['line']:>5}  {row['over']:>6}  {row['under']:>6}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
