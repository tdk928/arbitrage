from __future__ import annotations

"""Seed curated market rules into Postgres."""

from sqlalchemy.orm import Session

from scraper.models_v3 import MarketRuleSet, MarketRuleSiteMatch

TOTAL_GOALS_OU_SLUG = "total_goals_ou"
BOTH_TEAMS_TO_SCORE_SLUG = "both_teams_to_score"
MATCH_RESULT_1X2_SLUG = "match_result_1x2"
TOTAL_CORNERS_OU_SLUG = "total_corners_ou"
TOTAL_CARDS_OU_SLUG = "total_cards_ou"
FIRST_HALF_TOTAL_GOALS_OU_SLUG = "first_half_total_goals_ou"

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
    {
        "bookmaker_slug": "betano",
        "platform": "betano",
        "ui_label": "Над/Под Общо голове",
        "match_criteria": {
            "type_id": 13,
            "market_name": "Над/Под Общо голове",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "Betano typeId 13 — match total goals O/U",
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
    {
        "bookmaker_slug": "betano",
        "platform": "betano",
        "ui_label": "Двата отбора да отбележат",
        "match_criteria": {
            "type_id": 15,
            "market_name": "Двата отбора да отбележат",
            "market_name_exact": True,
            "required_outcome_roles": ["yes", "no"],
        },
        "notes": "Betano typeId 15 — match BTTS",
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
    {
        "bookmaker_slug": "betano",
        "platform": "betano",
        "ui_label": "Краен резултат Супер Коефициенти",
        "match_criteria": {
            "type_id": 2850,
            "market_name": "Краен резултат Супер Коефициенти",
            "market_name_exact": True,
            "required_outcome_roles": ["1", "X", "2"],
        },
        "notes": "Betano typeId 2850 — Супер Коефициенти 1X2 (UI default on WC matches)",
    },
]


_EGT_CORNERS_CRITERIA = {
    "market_name_contains": "total corners",
    "market_name_excludes_any": [
        "half",
        "1st",
        "2nd",
        " - ",
        "handicap",
        "range",
        "race",
        "odd/even",
        "corner 1x2",
        "1st corner",
        "last corner",
        "exact",
    ],
    "line_filter": "half_only",
    "required_outcome_roles": ["over", "under"],
}

CORNERS_SITE_ROWS: list[dict] = [
    {
        "bookmaker_slug": "winbet",
        "platform": "egt",
        "ui_label": "Алт. Брой Корнери / Брой Корнери",
        "match_criteria": _EGT_CORNERS_CRITERIA,
        "notes": "EGT — match total corners O/U (.5 lines), alt + default sections",
    },
    {
        "bookmaker_slug": "inbet",
        "platform": "egt",
        "ui_label": "Алт. Брой Корнери / Брой Корнери",
        "match_criteria": _EGT_CORNERS_CRITERIA,
        "notes": "Same EGT corners criteria as winbet",
    },
    {
        "bookmaker_slug": "efbet",
        "platform": "efbet",
        "ui_label": "Брой корнери",
        "match_criteria": {
            "original_name_contains": "Брой корнери",
            "original_name_excludes_any": [
                "полувреме",
                "1-во",
                "2-ро",
                "хендикап",
                " - ",
                "интервал",
                "нечет",
                "първи",
                "последен",
                "точен",
            ],
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "efbet match corners O/U — .5 lines + default mainLine",
    },
    {
        "bookmaker_slug": "palmsbet",
        "platform": "altenar",
        "ui_label": "Общ брой корнери",
        "match_criteria": {
            "type_id": 166,
            "market_name": "Общ брой корнери",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "Altenar typeId 166 — match total corners",
    },
    {
        "bookmaker_slug": "8888",
        "platform": "sportinno",
        "ui_label": "Брой Корнери",
        "match_criteria": {
            "type_id": 134,
            "market_group_name": "Брой Корнери",
            "market_name_excludes_any": ["полувреме", "1-во", "2-ро", "домакин", "гост"],
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "SportInno typeId 134 — full match corners (90 min)",
    },
    {
        "bookmaker_slug": "betano",
        "platform": "betano",
        "ui_label": "Корнери Над/Под",
        "match_criteria": {
            "type_id": 34,
            "market_name": "Корнери Над/Под",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "Betano typeId 34 — match total corners O/U",
    },
]


_EGT_CARDS_CRITERIA = {
    "market_name_contains": "total bookings",
    "market_name_excludes_any": [
        "half",
        "1st",
        "2nd",
        " - ",
        "handicap",
        "exact",
        "booking 1x2",
        "booking points",
        "minute",
        "european",
    ],
    "line_filter": "half_only",
    "required_outcome_roles": ["over", "under"],
}

CARDS_SITE_ROWS: list[dict] = [
    {
        "bookmaker_slug": "winbet",
        "platform": "egt",
        "ui_label": "Алт. Брой Картони / Брой Картони",
        "match_criteria": _EGT_CARDS_CRITERIA,
        "notes": "EGT — match total cards O/U (.5 lines), alt + default sections (Total Bookings)",
    },
    {
        "bookmaker_slug": "inbet",
        "platform": "egt",
        "ui_label": "Алт. Брой Картони / Брой Картони",
        "match_criteria": _EGT_CARDS_CRITERIA,
        "notes": "Same EGT cards criteria as winbet",
    },
    {
        "bookmaker_slug": "efbet",
        "platform": "efbet",
        "ui_label": "Брой картони",
        "match_criteria": {
            "original_name_contains": "Брой картони",
            "original_name_excludes_any": [
                "полувреме",
                "1-во",
                "2-ро",
                "хендикап",
                " - ",
                "интервал",
                "нечет",
                "първи",
                "последен",
                "точен",
                "червен",
                "жълт",
            ],
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "efbet match cards O/U — .5 lines + default mainLine",
    },
    {
        "bookmaker_slug": "palmsbet",
        "platform": "altenar",
        "ui_label": "Общ брой картони",
        "match_criteria": {
            "type_id": 139,
            "market_name": "Общ брой картони",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "Altenar typeId 139 — match total cards (slider O/U groups)",
    },
    {
        "bookmaker_slug": "8888",
        "platform": "sportinno",
        "ui_label": "Брой Картони",
        "match_criteria": {
            "type_id": 169,
            "market_group_name": "Брой Картони",
            "market_name_excludes_any": ["полувреме", "1-во", "2-ро", "домакин", "гост"],
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "SportInno typeId 169 — full match cards (90 min)",
    },
    {
        "bookmaker_slug": "betano",
        "platform": "betano",
        "ui_label": "Общо картони Над/Под",
        "match_criteria": {
            "type_id": 65,
            "market_name": "Общо картони Над/Под",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "Betano typeId 65 — match total cards O/U",
    },
]


_EGT_1H_GOALS_CRITERIA = {
    "radar_template": "total1stHalf",
    "market_name_contains": "1st half - total goals",
    "market_name_excludes_any": [
        "&",
        "multigoals",
        "exact",
        "odd/even",
        "halftime/fulltime",
    ],
    "line_filter": "half_only",
    "required_outcome_roles": ["over", "under"],
}

FIRST_HALF_GOALS_SITE_ROWS: list[dict] = [
    {
        "bookmaker_slug": "winbet",
        "platform": "egt",
        "ui_label": "Алт. 1-во Полувреме - Брой Голове",
        "match_criteria": _EGT_1H_GOALS_CRITERIA,
        "notes": "EGT — 1st half total goals O/U (.5 lines), alt + default sections",
    },
    {
        "bookmaker_slug": "inbet",
        "platform": "egt",
        "ui_label": "Алт. 1-во Полувреме - Брой Голове",
        "match_criteria": _EGT_1H_GOALS_CRITERIA,
        "notes": "Same EGT 1H goals criteria as winbet",
    },
    {
        "bookmaker_slug": "efbet",
        "platform": "efbet",
        "ui_label": "Голове през 1-во Полувреме",
        "match_criteria": {
            "original_name_contains": "Голове през 1-во Полувреме",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "efbet 1st half goals O/U — .5 lines + default mainLine",
    },
    {
        "bookmaker_slug": "palmsbet",
        "platform": "altenar",
        "ui_label": "1во полувреме - Общ брой голове",
        "match_criteria": {
            "type_id": 68,
            "market_name": "1во полувреме - Общ брой голове",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "Altenar typeId 68 — 1st half total goals (slider O/U groups)",
    },
    {
        "bookmaker_slug": "8888",
        "platform": "sportinno",
        "ui_label": "1-во Полувреме - Брой Голове",
        "match_criteria": {
            "type_id": 82,
            "market_group_name": "1-во Полувреме - Брой Голове",
            "line_filter": "half_only",
            "required_outcome_roles": ["over", "under"],
        },
        "notes": "SportInno typeId 82 — 1st half total goals",
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


def seed_total_corners_ou(session: Session) -> MarketRuleSet:
    rule = (
        session.query(MarketRuleSet)
        .filter(MarketRuleSet.slug == TOTAL_CORNERS_OU_SLUG)
        .one_or_none()
    )
    if not rule:
        rule = MarketRuleSet(
            slug=TOTAL_CORNERS_OU_SLUG,
            label="Over/Under Total Corners (match)",
            description=(
                "Match total corners Over/Under. Lines must end in .5 only "
                "(6.5, 7.5, 8.5 …). Includes default/main and alt lines."
            ),
            outcome_roles=["over", "under"],
            scope="global",
            line_filter="half_only",
            is_active=True,
        )
        session.add(rule)
        session.flush()

    _seed_rule_sites(session, rule, CORNERS_SITE_ROWS)
    session.flush()
    session.refresh(rule)
    return rule


def seed_total_cards_ou(session: Session) -> MarketRuleSet:
    rule = (
        session.query(MarketRuleSet)
        .filter(MarketRuleSet.slug == TOTAL_CARDS_OU_SLUG)
        .one_or_none()
    )
    if not rule:
        rule = MarketRuleSet(
            slug=TOTAL_CARDS_OU_SLUG,
            label="Over/Under Total Cards (match)",
            description=(
                "Match total cards/bookings Over/Under. Lines must end in .5 only "
                "(1.5, 2.5, 3.5 …). Includes default/main and alt lines."
            ),
            outcome_roles=["over", "under"],
            scope="global",
            line_filter="half_only",
            is_active=True,
        )
        session.add(rule)
        session.flush()

    _seed_rule_sites(session, rule, CARDS_SITE_ROWS)
    session.flush()
    session.refresh(rule)
    return rule


def seed_first_half_total_goals_ou(session: Session) -> MarketRuleSet:
    rule = (
        session.query(MarketRuleSet)
        .filter(MarketRuleSet.slug == FIRST_HALF_TOTAL_GOALS_OU_SLUG)
        .one_or_none()
    )
    if not rule:
        rule = MarketRuleSet(
            slug=FIRST_HALF_TOTAL_GOALS_OU_SLUG,
            label="Over/Under 1st Half Total Goals",
            description=(
                "First half total goals Over/Under. Lines must end in .5 only "
                "(0.5, 1.5, 2.5 …). Includes default/main and alt lines."
            ),
            outcome_roles=["over", "under"],
            scope="1h",
            line_filter="half_only",
            is_active=True,
        )
        session.add(rule)
        session.flush()

    _seed_rule_sites(session, rule, FIRST_HALF_GOALS_SITE_ROWS)
    session.flush()
    session.refresh(rule)
    return rule


def seed_all_rules(session: Session) -> list[MarketRuleSet]:
    return [
        seed_total_goals_ou(session),
        seed_both_teams_to_score(session),
        seed_match_result_1x2(session),
        seed_total_corners_ou(session),
        seed_total_cards_ou(session),
        seed_first_half_total_goals_ou(session),
    ]
