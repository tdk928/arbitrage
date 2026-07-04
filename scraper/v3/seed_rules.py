from __future__ import annotations

"""Seed curated market rules into Postgres."""

from sqlalchemy.orm import Session

from scraper.models_v3 import MarketRuleSet, MarketRuleSiteMatch

TOTAL_GOALS_OU_SLUG = "total_goals_ou"

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

    for row in SITE_ROWS:
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
    session.flush()
    session.refresh(rule)
    return rule


def seed_all_rules(session: Session) -> list[MarketRuleSet]:
    return [seed_total_goals_ou(session)]
