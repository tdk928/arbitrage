from __future__ import annotations

from scraper.v2.types import ParsedOutcome
from scraper.v3.criteria import criteria_match
from scraper.v3.seed_rules import SITE_ROWS as GOALS_SITE_ROWS
from scraper.v3.seed_rules import BTTS_SITE_ROWS
from scraper.v3.seed_rules import MATCH_RESULT_SITE_ROWS


def test_betano_goals_criteria_matches_type_id_and_half_lines(make_market):
    criteria = next(r["match_criteria"] for r in GOALS_SITE_ROWS if r["bookmaker_slug"] == "betano")

    match = make_market(
        market_name="Над/Под Общо голове 2.5",
        line="2.5",
        provider_template="typeid:13",
        specifiers={"type_id": 13},
    )
    assert criteria_match(criteria, match) is True

    whole_line = make_market(
        market_name="Над/Под Общо голове 2",
        line="2",
        provider_template="typeid:13",
        specifiers={"type_id": 13},
    )
    assert criteria_match(criteria, whole_line) is False

    wrong_type = make_market(
        market_name="Над/Под Общо голове 2.5",
        line="2.5",
        provider_template="typeid:15",
        specifiers={"type_id": 15},
    )
    assert criteria_match(criteria, wrong_type) is False


def test_betano_goals_market_name_prefix_match(make_market):
    criteria = next(r["match_criteria"] for r in GOALS_SITE_ROWS if r["bookmaker_slug"] == "betano")
    match = make_market(
        market_name="Над/Под Общо голове 1.5",
        line="1.5",
        specifiers={"type_id": 13},
    )
    assert criteria_match(criteria, match) is True


def test_betano_btts_criteria(make_market):
    criteria = next(r["match_criteria"] for r in BTTS_SITE_ROWS if r["bookmaker_slug"] == "betano")
    match = make_market(
        market_name="Двата отбора да отбележат",
        line=None,
        outcomes=[
            ParsedOutcome(role="yes", name="Да", odd=2.1),
            ParsedOutcome(role="no", name="Не", odd=1.7),
        ],
        specifiers={"type_id": 15},
        provider_template="typeid:15",
    )
    assert criteria_match(criteria, match) is True


def test_betano_super_odds_1x2_exact_name(make_market):
    criteria = next(r["match_criteria"] for r in MATCH_RESULT_SITE_ROWS if r["bookmaker_slug"] == "betano")
    match = make_market(
        market_name="Краен резултат Супер Коефициенти",
        line=None,
        outcomes=[
            ParsedOutcome(role="1", name="1", odd=1.65),
            ParsedOutcome(role="X", name="X", odd=4.0),
            ParsedOutcome(role="2", name="2", odd=6.0),
        ],
        specifiers={"type_id": 2850},
        provider_template="typeid:2850",
    )
    assert criteria_match(criteria, match) is True

    plain_1x2 = make_market(
        market_name="Краен резултат",
        line=None,
        outcomes=[
            ParsedOutcome(role="1", name="1", odd=1.65),
            ParsedOutcome(role="X", name="X", odd=4.0),
            ParsedOutcome(role="2", name="2", odd=6.0),
        ],
        specifiers={"type_id": 1},
        provider_template="typeid:1",
    )
    assert criteria_match(criteria, plain_1x2) is False


def test_efbet_goals_original_name_excludes_half_time(make_market):
    criteria = next(r["match_criteria"] for r in GOALS_SITE_ROWS if r["bookmaker_slug"] == "efbet")
    match = make_market(
        market_name="Голове",
        line="2.5",
        specifiers={"original_name": "Голове в Мача 2.5"},
    )
    assert criteria_match(criteria, match) is True

    half = make_market(
        market_name="Голове",
        line="1.5",
        specifiers={"original_name": "Голове в 1-во полувреме 1.5"},
    )
    assert criteria_match(criteria, half) is False


def test_palmsbet_type_id_and_exact_market_name(make_market):
    criteria = next(r["match_criteria"] for r in GOALS_SITE_ROWS if r["bookmaker_slug"] == "palmsbet")
    match = make_market(
        market_name="Общ брой голове",
        line="2.5",
        specifiers={"type_id": 18},
        provider_template="typeid:18",
        platform="altenar",
        bookmaker_slug="palmsbet",
    )
    assert criteria_match(criteria, match) is True

    wrong_type = make_market(
        market_name="Общ брой голове",
        line="2.5",
        specifiers={"type_id": 68},
        platform="altenar",
        bookmaker_slug="palmsbet",
    )
    assert criteria_match(criteria, wrong_type) is False
