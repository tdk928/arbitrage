from __future__ import annotations

"""Seed curated market rules into Postgres."""

from sqlalchemy.orm import Session

from scraper.models_v3 import MarketRuleSet, MarketRuleSiteMatch

TOTAL_GOALS_OU_SLUG = "total_goals_ou"
BOTH_TEAMS_TO_SCORE_SLUG = "both_teams_to_score"
MATCH_RESULT_1X2_SLUG = "match_result_1x2"

_EGT_GOALS_CRITERIA = {
    "ui_section_contains": "Алт. Брой Голове",
    "radar_template": "total",
    "market_name_contains_any": ["goal", "gолов", "total goals", "брой голове"],
    "market_name_excludes_any": ["corner", "корнер", "half", "1st", "2nd", "&"],
    "line_filter": "half_only",
    "required_outcome_roles": ["over", "under"],
}

SITE_ROWS: list[dict] = [
    {
        "bookmaker_slug": "winbet",
        "platform": "egt",
        "ui_label": "Алт. Брой Голове",
        "match_criteria": _EGT_GOALS_CRITERIA,
        "notes": "EGT Digital — Alt. total goals, .5 lines only",
    },
    {
        "bookmaker_slug": "inbet",
        "platform": "egt",
        "ui_label": "Алт. Брой Голове",
        "match_criteria": _EGT_GOALS_CRITERIA,
        "notes": "Same EGT criteria as winbet",
    },
    {
        "bookmaker_slug": "efbet",
        "platform": "efbet",
        "ui_label": "Голове в Мача",
        "match_criteria": {
            "original_name_contains": "Голове в Мача",
            "original_name_excludes_any": ["полувреме", "1-во", "2-ро"],
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "efbet Totals — match goals O/U (originalName prefix)",
    },
    {
        "bookmaker_slug": "palmsbet",
        "platform": "altenar",
        "ui_label": "Общ брой голове",
        "match_criteria": {
            "type_id": 18,
            "market_name": "Общ брой голове",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "Altenar typeId 18 — total goals",
    },
    {
        "bookmaker_slug": "8888",
        "platform": "sportinno",
        "ui_label": "Брой Голове",
        "match_criteria": {
            "type_id": 24,
            "market_group_name": "Брой Голове",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "SportInno typeId 24 — match total goals",
    },
]


_EGT_BTTS_CRITERIA = {
    "radar_template_any": ["BothTeamsToScore", "BothTeamsToScoreMarket"],
    "market_name_contains_any": ["двата отбора", "both teams"],
    "market_name_excludes_any": ["полувреме", "half", "1st", "2nd", "corner", "корнер", "&"],
    "required_outcome_roles": ["yes", "no"],
}

BTTS_SITE_ROWS: list[dict] = [
    {
        "bookmaker_slug": "winbet",
        "platform": "egt",
        "ui_label": "Двата Отбора Да Отбележат",
        "match_criteria": _EGT_BTTS_CRITERIA,
        "notes": "EGT Digital — both teams to score (match)",
    },
    {
        "bookmaker_slug": "inbet",
        "platform": "egt",
        "ui_label": "Двата Отбора Да Отбележат",
        "match_criteria": _EGT_BTTS_CRITERIA,
        "notes": "Same EGT BTTS criteria as winbet",
    },
    {
        "bookmaker_slug": "efbet",
        "platform": "efbet",
        "ui_label": "Двата Отбора да Отбележат Гол",
        "match_criteria": {
            "market_name": "Двата Отбора да Отбележат Гол",
            "market_name_exact": True,
            "required_outcome_roles": ["yes", "no"],
        },
        "notes": "efbet BTTS — plain match market only (no combos/halves)",
    },
    {
        "bookmaker_slug": "palmsbet",
        "platform": "altenar",
        "ui_label": "Двата отбора да отбележат",
        "match_criteria": {
            "type_id": 29,
            "market_name": "Двата отбора да отбележат гол",
            "market_name_exact": True,
            "required_outcome_roles": ["yes", "no"],
        },
        "notes": "Altenar typeId 29 — both teams to score",
    },
    {
        "bookmaker_slug": "8888",
        "platform": "sportinno",
        "ui_label": "Двата Отбора да Отбележат Гол",
        "match_criteria": {
            "type_id": 67,
            "market_group_name": "Двата Отбора да Отбележат Гол",
            "required_outcome_roles": ["yes", "no"],
        },
        "notes": "SportInno typeId 67 — full match BTTS (halves are typeId 119/120)",
    },
]


_EGT_1X2_CRITERIA = {
    "radar_template": "3Way",
    "market_name_contains_any": ["full time result", "краен резултат"],
    "market_name_excludes_any": ["полувреме", "half", "1st", "2nd", "&", "enhanced"],
    "required_outcome_roles": ["1", "X", "2"],
}

_INBET_1X2_CRITERIA = {
    "radar_template": "3Way",
    "market_name_contains": "enhanced odds",
    "required_outcome_roles": ["1", "X", "2"],
}

MATCH_RESULT_SITE_ROWS: list[dict] = [
    {
        "bookmaker_slug": "winbet",
        "platform": "egt",
        "ui_label": "Краен Резултат",
        "match_criteria": _EGT_1X2_CRITERIA,
        "notes": "EGT Digital — full-time 1X2",
    },
    {
        "bookmaker_slug": "inbet",
        "platform": "egt",
        "ui_label": "Краен Резултат 0% Марж",
        "match_criteria": _INBET_1X2_CRITERIA,
        "notes": "EGT Digital — 0% margin promo 1X2 (Enhanced Odds)",
    },
    {
        "bookmaker_slug": "efbet",
        "platform": "efbet",
        "ui_label": "Краен Резултат",
        "match_criteria": {
            "market_name": "Краен Резултат",
            "market_name_exact": True,
            "required_outcome_roles": ["1", "X", "2"],
        },
        "notes": "efbet plain full-time 1X2 (excludes early payout / combos)",
    },
    {
        "bookmaker_slug": "palmsbet",
        "platform": "altenar",
        "ui_label": "1x2",
        "match_criteria": {
            "type_id": 1,
            "market_name": "1x2",
            "market_name_exact": True,
            "required_outcome_roles": ["1", "X", "2"],
        },
        "notes": "Altenar typeId 1 — full-time 1X2",
    },
    {
        "bookmaker_slug": "8888",
        "platform": "sportinno",
        "ui_label": "Краен Резултат",
        "match_criteria": {
            "type_id": 10000023,
            "market_group_name": "Краен Резултат",
            "required_outcome_roles": ["1", "X", "2"],
        },
        "notes": "SportInno typeId 10000023 — plain 1X2 (not PAY/combo variant typeId 23)",
    },
]


def _seed_rule_sites(session: Session, rule: MarketRuleSet, site_rows: list[dict]) -> None:
    for row in site_rows:
        existing = (
            session.query(MarketRuleSiteMatch)
            .filter(
                MarketRuleSiteMatch.rule_set_id == rule.id,
                MarketRuleSiteMatch.bookmaker_slug == row["bookmaker_slug"],
            )
            .one_or_none()
        )
        if existing:
            existing.platform = row["platform"]
            existing.ui_label = row["ui_label"]
            existing.match_criteria = row["match_criteria"]
            existing.notes = row["notes"]
            existing.is_active = True
        else:
            session.add(
                MarketRuleSiteMatch(
                    rule_set_id=rule.id,
                    bookmaker_slug=row["bookmaker_slug"],
                    platform=row["platform"],
                    ui_label=row["ui_label"],
                    match_criteria=row["match_criteria"],
                    notes=row["notes"],
                    is_active=True,
                )
            )


def seed_total_goals_ou(session: Session) -> MarketRuleSet:
    rule = session.query(MarketRuleSet).filter(MarketRuleSet.slug == TOTAL_GOALS_OU_SLUG).one_or_none()
    if not rule:
        rule = MarketRuleSet(
            slug=TOTAL_GOALS_OU_SLUG,
            label="Over/Under Total Goals (match)",
            description=(
                "Match total goals Over/Under. Lines must end in .5 only "
                "(0.5, 1.5, 2.5 …). Excludes .25/.75 and whole numbers 1, 2, 3."
            ),
            outcome_roles=["over", "under"],
            scope="global",
            line_filter="half_only",
            is_active=True,
        )
        session.add(rule)
        session.flush()

    _seed_rule_sites(session, rule, SITE_ROWS)
    session.flush()
    session.refresh(rule)
    return rule


def seed_both_teams_to_score(session: Session) -> MarketRuleSet:
    rule = (
        session.query(MarketRuleSet)
        .filter(MarketRuleSet.slug == BOTH_TEAMS_TO_SCORE_SLUG)
        .one_or_none()
    )
    if not rule:
        rule = MarketRuleSet(
            slug=BOTH_TEAMS_TO_SCORE_SLUG,
            label="Both Teams To Score (match)",
            description="Both teams to score Yes/No for the full match.",
            outcome_roles=["yes", "no"],
            scope="global",
            line_filter="none",
            is_active=True,
        )
        session.add(rule)
        session.flush()

    _seed_rule_sites(session, rule, BTTS_SITE_ROWS)
    session.flush()
    session.refresh(rule)
    return rule


def seed_match_result_1x2(session: Session) -> MarketRuleSet:
    rule = (
        session.query(MarketRuleSet)
        .filter(MarketRuleSet.slug == MATCH_RESULT_1X2_SLUG)
        .one_or_none()
    )
    if not rule:
        rule = MarketRuleSet(
            slug=MATCH_RESULT_1X2_SLUG,
            label="Match Result 1X2 (full time)",
            description="Full-time match result: home win (1), draw (X), away win (2).",
            outcome_roles=["1", "X", "2"],
            scope="global",
            line_filter="none",
            is_active=True,
        )
        session.add(rule)
        session.flush()

    _seed_rule_sites(session, rule, MATCH_RESULT_SITE_ROWS)
    session.flush()
    session.refresh(rule)
    return rule


def seed_all_rules(session: Session) -> list[MarketRuleSet]:
    return [
        seed_total_goals_ou(session),
        seed_both_teams_to_score(session),
        seed_match_result_1x2(session),
    ]
