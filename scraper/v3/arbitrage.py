from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, aliased

from scraper.models import Bookmaker, Match, Team
from scraper.models_v3 import (
    ArbitrageAudit,
    ArbitrageTop10Current,
    MarketOddsV3,
    MarketRuleSet,
)
from scraper.normalize import normalize_team
from scraper.v2.arbitrage import compute_arbitrage_v2


@dataclass
class OpportunityV3:
    rule_set_id: int
    rule_slug: str
    line: str
    margin_pct: float
    implied_total: float
    legs: list[dict[str, Any]]
    bookmaker_count: int
    home_team: str
    away_team: str
    kickoff_utc: datetime | None
    market_label: str


def compute_opportunities_v3(
    session: Session,
    scrape_run_id: int,
    min_margin: float = 1.0,
) -> list[OpportunityV3]:
    HomeTeam = aliased(Team)
    AwayTeam = aliased(Team)
    rows = (
        session.query(MarketOddsV3, Match, HomeTeam, AwayTeam, Bookmaker, MarketRuleSet)
        .join(Match, Match.id == MarketOddsV3.match_id)
        .join(HomeTeam, HomeTeam.id == Match.home_team_id)
        .join(AwayTeam, AwayTeam.id == Match.away_team_id)
        .join(Bookmaker, Bookmaker.id == MarketOddsV3.bookmaker_id)
        .join(MarketRuleSet, MarketRuleSet.id == MarketOddsV3.rule_set_id)
        .filter(MarketOddsV3.scrape_run_id == scrape_run_id)
        .all()
    )

    grouped: dict[tuple[str, str, int, str], dict[str, Any]] = defaultdict(
        lambda: {"bookmaker_odds": {}, "meta": None}
    )

    for odds, match, home, away, bm, rule in rows:
        nh, na = normalize_team(home.name), normalize_team(away.name)
        pair = tuple(sorted([nh, na]))
        key = (pair[0], pair[1], rule.id, odds.line)
        entry = grouped[key]
        entry["bookmaker_odds"][bm.slug] = odds.outcomes
        if entry["meta"] is None:
            entry["meta"] = {
                "rule_set_id": rule.id,
                "rule_slug": rule.slug,
                "line": odds.line,
                "market_label": f"{rule.label} {odds.line}",
                "home_team": home.name,
                "away_team": away.name,
                "kickoff_utc": match.kickoff_utc,
                "outcome_roles": rule.outcome_roles or ["over", "under"],
            }
        elif len(entry["bookmaker_odds"]) == 1:
            # second bookmaker — prefer latin-script team names when available
            for field, new_val in (("home_team", home.name), ("away_team", away.name)):
                if sum(1 for c in new_val if ord(c) < 128) > sum(
                    1 for c in entry["meta"][field] if ord(c) < 128
                ):
                    entry["meta"][field] = new_val

    opportunities: list[OpportunityV3] = []
    for entry in grouped.values():
        meta = entry["meta"]
        if not meta:
            continue
        roles = list(meta["outcome_roles"])
        result = compute_arbitrage_v2(roles, entry["bookmaker_odds"], min_margin=min_margin)
        if not result:
            continue
        opportunities.append(
            OpportunityV3(
                rule_set_id=meta["rule_set_id"],
                rule_slug=meta["rule_slug"],
                line=meta["line"],
                margin_pct=result.margin_pct,
                implied_total=result.implied_total,
                legs=result.legs,
                bookmaker_count=result.bookmaker_count,
                home_team=meta["home_team"],
                away_team=meta["away_team"],
                kickoff_utc=meta["kickoff_utc"],
                market_label=meta["market_label"],
            )
        )

    return opportunities


def persist_top10_and_audit(
    session: Session,
    scrape_run_id: int,
    opportunities: list[OpportunityV3],
    limit: int = 10,
) -> list[OpportunityV3]:
    ranked = sorted(opportunities, key=lambda o: o.margin_pct, reverse=True)[:limit]
    captured_at = datetime.now(tz=timezone.utc)

    session.query(ArbitrageTop10Current).delete()

    for rank, opp in enumerate(ranked, start=1):
        session.add(
            ArbitrageTop10Current(
                rank=rank,
                scrape_run_id=scrape_run_id,
                rule_set_id=opp.rule_set_id,
                rule_slug=opp.rule_slug,
                line=opp.line,
                margin_pct=opp.margin_pct,
                implied_total=opp.implied_total,
                bookmaker_count=opp.bookmaker_count,
                home_team=opp.home_team,
                away_team=opp.away_team,
                kickoff_utc=opp.kickoff_utc,
                market_label=opp.market_label,
                legs=opp.legs,
                captured_at=captured_at,
            )
        )
        session.add(
            ArbitrageAudit(
                scrape_run_id=scrape_run_id,
                captured_at=captured_at,
                rank=rank,
                rule_set_id=opp.rule_set_id,
                rule_slug=opp.rule_slug,
                line=opp.line,
                margin_pct=opp.margin_pct,
                implied_total=opp.implied_total,
                bookmaker_count=opp.bookmaker_count,
                home_team=opp.home_team,
                away_team=opp.away_team,
                kickoff_utc=opp.kickoff_utc,
                market_label=opp.market_label,
                legs=opp.legs,
            )
        )

    session.flush()
    return ranked
