from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from scraper.models_v2 import (
    ArbitrageOpportunityV2,
    CanonicalMarketV2,
    OddsSnapshotV2,
    RawMarketV2,
    ScrapeRunV2,
)
from scraper.arbitrage import allocate_stakes
from scraper.models import Match, Team


def build_opportunities_response(
    session: Session,
    run_id: int,
    scraped_at: str,
    min_margin: float,
    limit: int,
    budget_eur: float,
) -> dict[str, Any]:
    run = session.get(ScrapeRunV2, run_id)
    opp_rows = (
        session.query(ArbitrageOpportunityV2, Match, CanonicalMarketV2)
        .join(Match, Match.id == ArbitrageOpportunityV2.match_id)
        .join(
            CanonicalMarketV2,
            CanonicalMarketV2.id == ArbitrageOpportunityV2.canonical_market_id,
        )
        .filter(
            ArbitrageOpportunityV2.scrape_run_id == run_id,
            ArbitrageOpportunityV2.margin_pct >= min_margin,
        )
        .order_by(ArbitrageOpportunityV2.margin_pct.desc())
        .limit(limit)
        .all()
    )

    bets = []
    for opp, match, canonical in opp_rows:
        home = session.get(Team, match.home_team_id)
        away = session.get(Team, match.away_team_id)
        odds = [leg["odd"] for leg in opp.legs]
        stakes, guaranteed, profit = allocate_stakes(budget_eur, odds)
        legs_out = [{**leg, "stake_eur": stake} for leg, stake in zip(opp.legs, stakes)]
        bets.append(
            {
                "match": f"{home.name if home else '?'} vs {away.name if away else '?'}",
                "kickoff_utc": match.kickoff_utc.isoformat(),
                "market": canonical.label,
                "family": canonical.family,
                "margin_pct": float(opp.margin_pct),
                "bookmaker_count": opp.bookmaker_count,
                "legs": legs_out,
                "budget_eur": budget_eur,
                "guaranteed_return_eur": guaranteed,
                "profit_eur": profit,
            }
        )

    return {
        "run_id": run_id,
        "pipeline_version": "v2",
        "scraped_at": scraped_at,
        "min_margin_pct": min_margin,
        "count": len(bets),
        "bets": bets,
        "stats": run.stats if run else {},
    }


def build_markets_debug(
    session: Session,
    run_id: int,
    match_id: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    q = session.query(RawMarketV2, CanonicalMarketV2).outerjoin(
        CanonicalMarketV2, CanonicalMarketV2.id == RawMarketV2.canonical_market_id
    ).filter(RawMarketV2.scrape_run_id == run_id)

    if match_id is not None:
        q = q.filter(RawMarketV2.match_id == match_id)

    rows = q.limit(limit).all()
    markets = []
    for raw, canonical in rows:
        markets.append(
            {
                "match_id": raw.match_id,
                "bookmaker_id": raw.bookmaker_id,
                "market_name": raw.market_name,
                "mapped": raw.mapped,
                "canonical_label": canonical.label if canonical else None,
                "family": canonical.family if canonical else None,
                "outcomes": raw.outcomes,
            }
        )

    cross_q = (
        session.query(
            OddsSnapshotV2.match_id,
            OddsSnapshotV2.canonical_market_id,
            CanonicalMarketV2.label,
        )
        .join(CanonicalMarketV2, CanonicalMarketV2.id == OddsSnapshotV2.canonical_market_id)
        .filter(OddsSnapshotV2.scrape_run_id == run_id)
    )
    if match_id is not None:
        cross_q = cross_q.filter(OddsSnapshotV2.match_id == match_id)

    from collections import defaultdict

    grouped: dict[tuple[int, int], list] = defaultdict(list)
    labels: dict[tuple[int, int], str] = {}
    for mid, cid, label in cross_q.all():
        grouped[(mid, cid)].append(mid)
        labels[(mid, cid)] = label

    bm_counts = session.query(OddsSnapshotV2).filter(OddsSnapshotV2.scrape_run_id == run_id)
    if match_id is not None:
        bm_counts = bm_counts.filter(OddsSnapshotV2.match_id == match_id)

    cross_bookmaker = []
    seen: set[tuple[int, int]] = set()
    for snap in bm_counts.all():
        key = (snap.match_id, snap.canonical_market_id)
        if key in seen:
            continue
        seen.add(key)
        count = (
            session.query(OddsSnapshotV2)
            .filter(
                OddsSnapshotV2.scrape_run_id == run_id,
                OddsSnapshotV2.match_id == snap.match_id,
                OddsSnapshotV2.canonical_market_id == snap.canonical_market_id,
            )
            .count()
        )
        if count >= 2:
            cross_bookmaker.append(
                {
                    "match_id": snap.match_id,
                    "canonical_market_id": snap.canonical_market_id,
                    "label": labels.get(key, ""),
                    "bookmaker_count": count,
                }
            )

    return {
        "run_id": run_id,
        "raw_markets_sample": markets,
        "cross_bookmaker_markets": cross_bookmaker[:limit],
    }
