from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def roi_pct_from_implied(implied_sum: float) -> float:
    """ROI on total stake when splitting optimally across arb legs."""
    if implied_sum <= 0:
        return 0.0
    return (1.0 / implied_sum - 1.0) * 100.0


@dataclass
class OpportunityV2:
    canonical_market_id: int
    market_label: str
    family: str
    margin_pct: float
    implied_total: float
    legs: list[dict[str, Any]]
    bookmaker_count: int


def compute_arbitrage_v2(
    outcome_roles: list[str],
    bookmaker_odds: dict[str, list[dict[str, Any]]],
    min_margin: float = 1.0,
) -> OpportunityV2 | None:
    """
    bookmaker_odds: {bookmaker_slug: [{"role": "over", "name": "...", "odd": 1.9}, ...]}
    margin_pct field stores ROI%: (1/implied_sum - 1) * 100.
    """
    if len(outcome_roles) < 2:
        return None

    best_legs: list[dict[str, Any]] = []
    implied_sum = 0.0
    bookmakers_used: set[str] = set()

    for role in outcome_roles:
        best_odd = 0.0
        best_bm = None
        best_name = role
        for bm_slug, outcomes in bookmaker_odds.items():
            for o in outcomes:
                if o.get("role") == role:
                    odd = float(o["odd"])
                    if odd > best_odd:
                        best_odd = odd
                        best_bm = bm_slug
                        best_name = o.get("name", role)
        if not best_bm or best_odd <= 1.0:
            return None
        implied_sum += 1.0 / best_odd
        bookmakers_used.add(best_bm)
        best_legs.append(
            {
                "role": role,
                "outcome": best_name,
                "odd": round(best_odd, 4),
                "bookmaker": best_bm,
            }
        )

    if len(bookmakers_used) < 2:
        return None

    roi_pct = roi_pct_from_implied(implied_sum)
    if roi_pct < min_margin:
        return None

    return OpportunityV2(
        canonical_market_id=0,
        market_label="",
        family="",
        margin_pct=round(roi_pct, 4),
        implied_total=round(implied_sum, 6),
        legs=best_legs,
        bookmaker_count=len(bookmakers_used),
    )


def rank_opportunities_v2(
    opportunities: list[OpportunityV2],
    limit: int = 10,
) -> list[OpportunityV2]:
    return sorted(opportunities, key=lambda o: o.margin_pct, reverse=True)[:limit]
