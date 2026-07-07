"""Probe Betano scraping for France vs Morocco (5 core markets)."""

from __future__ import annotations

import argparse
import sys

from scraper.platforms.betano import BetanoScraper
from scraper.v3.criteria import criteria_match
from scraper.v3.seed_rules import (
    BOTH_TEAMS_TO_SCORE_SLUG,
    MATCH_RESULT_1X2_SLUG,
    TOTAL_CARDS_OU_SLUG,
    TOTAL_CORNERS_OU_SLUG,
    TOTAL_GOALS_OU_SLUG,
)

PROBE_RULES = {
    TOTAL_GOALS_OU_SLUG: {
        "ui_label": "Над/Под Общо голове",
        "match_criteria": {
            "type_id": 13,
            "market_name": "Над/Под Общо голове",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
    },
    BOTH_TEAMS_TO_SCORE_SLUG: {
        "ui_label": "Двата отбора да отбележат",
        "match_criteria": {
            "type_id": 15,
            "market_name": "Двата отбора да отбележат",
            "market_name_exact": True,
            "required_outcome_roles": ["yes", "no"],
        },
    },
    MATCH_RESULT_1X2_SLUG: {
        "ui_label": "Краен резултат Супер Коефициенти",
        "match_criteria": {
            "type_id": 2850,
            "market_name": "Краен резултат Супер Коефициенти",
            "market_name_exact": True,
            "required_outcome_roles": ["1", "X", "2"],
        },
    },
    TOTAL_CORNERS_OU_SLUG: {
        "ui_label": "Корнери Над/Под",
        "match_criteria": {
            "type_id": 34,
            "market_name": "Корнери Над/Под",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
    },
    TOTAL_CARDS_OU_SLUG: {
        "ui_label": "Общо картони Над/Под",
        "match_criteria": {
            "type_id": 65,
            "market_name": "Общо картони Над/Под",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
    },
}

DISCOVERY_CONFIG = {
    "tournament_id": 189813,
    "tournament_slug": "svetovno-pervenstvo",
    "sport_slug": "futbol",
    "events_req": "la,s,stnf,c,mb,mbl",
}

MATCH_TERMS = ("франция", "france", "мароко", "morocco")


def _find_fixture(scraper: BetanoScraper):
    fixtures = scraper.list_fixtures(DISCOVERY_CONFIG)
    for fx in fixtures:
        text = f"{fx.home_team} {fx.away_team}".lower()
        if all(any(t in text for t in group) for group in (("франция", "france"), ("мароко", "morocco"))):
            return fx
    for fx in fixtures:
        text = f"{fx.home_team} {fx.away_team}".lower()
        if any(t in text for t in MATCH_TERMS):
            return fx
    return None


def _odd(market, role: str) -> float | None:
    for o in market.outcomes:
        if o.role == role:
            return o.odd
    return None


MAIN_LINES = {
    TOTAL_GOALS_OU_SLUG: "2.5",
    TOTAL_CORNERS_OU_SLUG: "9.5",
    TOTAL_CARDS_OU_SLUG: "3.5",
}


def _pick_main_line(slug: str, matched: list):
    preferred = MAIN_LINES.get(slug)
    if preferred:
        main = next((m for m in matched if m.line == preferred), None)
        if main:
            return main, [m for m in matched if m.line != preferred]
    matched = sorted(matched, key=lambda m: float(m.line or 0))
    return (matched[0], matched[1:]) if matched else (None, [])


def run_probe() -> int:
    scraper = BetanoScraper()
    fx = _find_fixture(scraper)
    if not fx:
        print("Fixture not found: France vs Morocco")
        return 1

    markets = scraper.fetch_parsed_markets(fx.external_id, DISCOVERY_CONFIG)
    print(f"Match: {fx.home_team} vs {fx.away_team}")
    print(f"Event ID: {fx.external_id}")
    print(f"Kickoff UTC: {fx.kickoff_utc.isoformat()}")
    print(f"Scraped markets (parsed): {len(markets)}")
    print()

    headers = f"{'Market':<28} {'Line':>5}  {'Side A':>8}  {'Odd A':>6}  {'Side B':>8}  {'Odd B':>6}"
    print(headers)
    print("-" * len(headers))

    for slug, rule in PROBE_RULES.items():
        criteria = rule["match_criteria"]
        matched = [m for m in markets if criteria_match(criteria, m)]
        if slug in (TOTAL_GOALS_OU_SLUG, TOTAL_CORNERS_OU_SLUG, TOTAL_CARDS_OU_SLUG):
            main, alt_lines = _pick_main_line(slug, matched)
            if not main:
                print(f"{slug:<28} {'—':>5}  {'—':>8}  {'—':>6}  {'—':>8}  {'—':>6}")
                continue
            if slug == TOTAL_GOALS_OU_SLUG:
                print(
                    f"{rule['ui_label']:<28} {main.line:>5}  {'Over':>8}  {_odd(main, 'over'):>6}  "
                    f"{'Under':>8}  {_odd(main, 'under'):>6}"
                )
            else:
                print(
                    f"{rule['ui_label']:<28} {main.line:>5}  {'Over':>8}  {_odd(main, 'over'):>6}  "
                    f"{'Under':>8}  {_odd(main, 'under'):>6}"
                )
            if alt_lines:
                preview_lines = sorted(alt_lines, key=lambda m: abs(float(m.line or 0) - float(main.line or 0)))[:3]
                alt_preview = ", ".join(
                    f"{m.line}: O {_odd(m, 'over')} / U {_odd(m, 'under')}" for m in preview_lines
                )
                print(f"{'':28} alt: {alt_preview}")
            continue

        if slug == BOTH_TEAMS_TO_SCORE_SLUG:
            main = matched[0] if matched else None
            if not main:
                print(f"{rule['ui_label']:<28} {'—':>5}  {'Yes':>8}  {'—':>6}  {'No':>8}  {'—':>6}")
                continue
            print(
                f"{rule['ui_label']:<28} {'—':>5}  {'Yes':>8}  {_odd(main, 'yes'):>6}  "
                f"{'No':>8}  {_odd(main, 'no'):>6}"
            )
            continue

        if slug == MATCH_RESULT_1X2_SLUG:
            main = matched[0] if matched else None
            if not main:
                print(f"{rule['ui_label']:<28} {'—':>5}  {'1':>8}  {'—':>6}  {'X':>8}  {'—':>6}")
                continue
            print(
                f"{rule['ui_label']:<28} {'—':>5}  {'1':>8}  {_odd(main, '1'):>6}  "
                f"{'X':>8}  {_odd(main, 'X'):>6}  | 2 {_odd(main, '2')}"
            )

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe Betano France vs Morocco markets")
    _ = parser.parse_args(argv)
    return run_probe()


if __name__ == "__main__":
    sys.exit(main())
