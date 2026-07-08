from __future__ import annotations

from scraper.v2.types import ParsedOutcome
from scraper.v3.seed_rules import (
    BTTS_SITE_ROWS,
    CARDS_SITE_ROWS,
    CORNERS_SITE_ROWS,
    MATCH_RESULT_SITE_ROWS,
    SITE_ROWS as GOALS_SITE_ROWS,
)

from tests.helpers import select_odds_rows_from_markets


def _betano_criteria(rows, slug):
    return next(r["match_criteria"] for r in rows if r["bookmaker_slug"] == slug)


def _all_betano_markets_for_event(make_market):
    """Synthetic full event payload — all Betano markets returned by one HTTP call."""
    return [
        make_market(
            market_name="Над/Под Общо голове 1.5",
            line="1.5",
            specifiers={"type_id": 13},
            provider_template="typeid:13",
        ),
        make_market(
            market_name="Над/Под Общо голове 2.5",
            line="2.5",
            specifiers={"type_id": 13},
            provider_template="typeid:13",
        ),
        make_market(
            market_name="Двата отбора да отбележат",
            line=None,
            outcomes=[
                ParsedOutcome(role="yes", name="Да", odd=2.15),
                ParsedOutcome(role="no", name="Не", odd=1.7),
            ],
            specifiers={"type_id": 15},
            provider_template="typeid:15",
        ),
        make_market(
            market_name="Краен резултат Супер Коефициенти",
            line=None,
            outcomes=[
                ParsedOutcome(role="1", name="1", odd=1.65),
                ParsedOutcome(role="X", name="X", odd=4.0),
                ParsedOutcome(role="2", name="2", odd=6.0),
            ],
            specifiers={"type_id": 2850},
            provider_template="typeid:2850",
        ),
        make_market(
            market_name="Корнери Над/Под 9.5",
            line="9.5",
            specifiers={"type_id": 34},
            provider_template="typeid:34",
        ),
        make_market(
            market_name="Общо картони Над/Под 4.5",
            line="4.5",
            specifiers={"type_id": 65},
            provider_template="typeid:65",
        ),
        make_market(
            market_name="Над/Под Общо голове 2",
            line="2",
            specifiers={"type_id": 13},
            provider_template="typeid:13",
        ),
    ]


def test_multi_rule_single_fetch_produces_same_rows_as_repeated_fetch(make_market):
    """
    Regression: one cached event payload must yield the same DB rows as
    fetching separately per rule (pipeline lines 173-206).
    """
    all_markets = _all_betano_markets_for_event(make_market)
    rules = [
        (1, "total_goals_ou", "half_only", _betano_criteria(GOALS_SITE_ROWS, "betano")),
        (2, "both_teams_to_score", "none", _betano_criteria(BTTS_SITE_ROWS, "betano")),
        (3, "match_result_1x2", "none", _betano_criteria(MATCH_RESULT_SITE_ROWS, "betano")),
        (4, "total_corners_ou", "half_only", _betano_criteria(CORNERS_SITE_ROWS, "betano")),
        (5, "total_cards_ou", "half_only", _betano_criteria(CARDS_SITE_ROWS, "betano")),
    ]

    shared_seen: set[tuple[int, int, int, str]] = set()
    shared_rows = []
    for rule_id, _slug, line_filter, criteria in rules:
        shared_rows.extend(
            select_odds_rows_from_markets(
                all_markets,
                rule_id=rule_id,
                rule_line_filter=line_filter,
                match_criteria=criteria,
                seen_odds_keys=shared_seen,
            )
        )

    per_rule_rows = []
    for rule_id, _slug, line_filter, criteria in rules:
        per_rule_rows.extend(
            select_odds_rows_from_markets(
                all_markets,
                rule_id=rule_id,
                rule_line_filter=line_filter,
                match_criteria=criteria,
                seen_odds_keys=set(),
            )
        )

    assert len(shared_rows) == len(per_rule_rows)
    assert {(r["rule_id"], r["line"], r["market_name"]) for r in shared_rows} == {
        (r["rule_id"], r["line"], r["market_name"]) for r in per_rule_rows
    }
    # goals 1.5 + 2.5, BTTS, 1X2, corners 9.5, cards 4.5; whole-line 2 excluded
    assert len(shared_rows) == 6


def test_dedup_prevents_duplicate_line_per_rule(make_market):
    criteria = _betano_criteria(GOALS_SITE_ROWS, "betano")
    markets = [
        make_market(
            market_name="Над/Под Общо голове 2.5",
            line="2.5",
            specifiers={"type_id": 13},
        ),
        make_market(
            market_name="Над/Под Общо голове 2.5",
            line="2.5",
            external_id="dup",
            specifiers={"type_id": 13},
        ),
    ]
    seen: set[tuple[int, int, int, str]] = set()
    rows = select_odds_rows_from_markets(
        markets,
        rule_id=1,
        rule_line_filter="half_only",
        match_criteria=criteria,
        seen_odds_keys=seen,
    )
    assert len(rows) == 1
