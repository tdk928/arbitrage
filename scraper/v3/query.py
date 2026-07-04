from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from scraper.models import Bookmaker, Match, Team
from scraper.models_v3 import MarketOddsV3, MarketRuleSet, ScrapeRunV3


def _latest_run_id(session: Session) -> int | None:
    run = (
        session.query(ScrapeRunV3)
        .filter(ScrapeRunV3.status.in_(("success", "partial")))
        .order_by(ScrapeRunV3.id.desc())
        .first()
    )
    return run.id if run else None


from scraper.normalize import normalize_team


def _team_matches(name: str, terms: tuple[str, ...]) -> bool:
    norm = normalize_team(name)
    for t in terms:
        tn = normalize_team(t)
        if tn in norm or norm in tn or tn in name.lower() or t.lower() in name.lower():
            return True
    return False


def fetch_market_odds(
    session: Session,
    rule_slug: str,
    home_terms: tuple[str, ...],
    away_terms: tuple[str, ...],
    run_id: int | None = None,
) -> dict[str, Any] | None:
    rule = (
        session.query(MarketRuleSet).filter(MarketRuleSet.slug == rule_slug).one_or_none()
    )
    if not rule:
        return None

    rid = run_id or _latest_run_id(session)
    if not rid:
        return None

    rows = (
        session.query(MarketOddsV3, Match, Bookmaker)
        .join(Match, Match.id == MarketOddsV3.match_id)
        .join(Bookmaker, Bookmaker.id == MarketOddsV3.bookmaker_id)
        .filter(
            MarketOddsV3.scrape_run_id == rid,
            MarketOddsV3.rule_set_id == rule.id,
        )
        .all()
    )

    match_ids: set[int] = set()
    filtered: list[tuple[MarketOddsV3, Bookmaker, Match, Team, Team]] = []

    for odds, match, bm in rows:
        home = session.get(Team, match.home_team_id)
        away = session.get(Team, match.away_team_id)
        if not home or not away:
            continue
        if not _team_matches(home.name, home_terms) and not _team_matches(away.name, home_terms):
            continue
        if not _team_matches(home.name, away_terms) and not _team_matches(away.name, away_terms):
            continue
        match_ids.add(match.id)
        filtered.append((odds, bm, match, home, away))

    if not filtered:
        return None

    # Prefer Latin display names when bookmakers disagree (Canada vs Morocco / Канада vs Мароко)
    def _ascii_score(name: str) -> int:
        return sum(1 for c in name if ord(c) < 128)

    ref_home, ref_away, ref_kickoff = filtered[0][3].name, filtered[0][4].name, filtered[0][2].kickoff_utc
    for _, _, match, home, away in filtered:
        if _ascii_score(home.name) + _ascii_score(away.name) > _ascii_score(ref_home) + _ascii_score(ref_away):
            ref_home, ref_away, ref_kickoff = home.name, away.name, match.kickoff_utc

    sites: dict[str, dict[str, Any]] = {}
    for odds, bm, _match, _home, _away in sorted(
        filtered, key=lambda x: (x[1].slug, float(x[0].line or 0))
    ):
        over = next((o["odd"] for o in odds.outcomes if o.get("role") == "over"), None)
        under = next((o["odd"] for o in odds.outcomes if o.get("role") == "under"), None)
        entry = sites.setdefault(
            bm.slug,
            {
                "ui_label": odds.ui_label,
                "event_id": odds.external_event_id,
                "lines": [],
            },
        )
        entry["lines"].append(
            {
                "line": odds.line,
                "market_name": odds.market_name,
                "over": over,
                "under": under,
            }
        )

    return {
        "run_id": rid,
        "rule": rule_slug,
        "home": ref_home,
        "away": ref_away,
        "kickoff_utc": ref_kickoff.isoformat(),
        "sites": sites,
    }
