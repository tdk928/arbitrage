from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MARKET_OUTCOME_MAP: dict[str, list[str]] = {
    "MATCH_1X2": ["1", "X", "2"],
    "GOALS_OU_25": ["Over", "Under"],
    "CORNERS_OU_85": ["Over", "Under"],
    "CORNERS_OU_95": ["Over", "Under"],
}


@dataclass
class OpportunityResult:
    market_code: str
    margin_pct: float
    implied_total: float
    legs: list[dict[str, Any]]
    bookmaker_count: int


def compute_arbitrage(
    market_code: str,
    bookmaker_odds: dict[str, list[dict[str, Any]]],
    min_margin: float = 1.0,
) -> OpportunityResult | None:
    """
    bookmaker_odds: {bookmaker_slug: [{"name": "1", "odd": 1.44}, ...]}
    """
    expected = MARKET_OUTCOME_MAP.get(market_code)
    if not expected:
        return None

    best_legs: list[dict[str, Any]] = []
    implied_sum = 0.0
    bookmakers_used: set[str] = set()

    for outcome_name in expected:
        best_odd = 0.0
        best_bm = None
        for bm_slug, outcomes in bookmaker_odds.items():
            for o in outcomes:
                if o.get("name") == outcome_name:
                    odd = float(o["odd"])
                    if odd > best_odd:
                        best_odd = odd
                        best_bm = bm_slug
        if not best_bm or best_odd <= 1.0:
            return None
        implied_sum += 1.0 / best_odd
        bookmakers_used.add(best_bm)
        best_legs.append(
            {
                "outcome": outcome_name,
                "odd": round(best_odd, 4),
                "bookmaker": best_bm,
            }
        )

    if len(bookmakers_used) < 2:
        return None

    margin_pct = (1.0 - implied_sum) * 100.0
    if margin_pct < min_margin:
        return None

    return OpportunityResult(
        market_code=market_code,
        margin_pct=round(margin_pct, 4),
        implied_total=round(implied_sum, 6),
        legs=best_legs,
        bookmaker_count=len(bookmakers_used),
    )


def rank_opportunities(
    opportunities: list[OpportunityResult],
    limit: int = 10,
) -> list[OpportunityResult]:
    return sorted(opportunities, key=lambda o: o.margin_pct, reverse=True)[:limit]


def allocate_stakes(budget_eur: float, odds: list[float]) -> tuple[list[float], float, float]:
    """Split budget across arb legs; return stakes, guaranteed return, profit."""
    implied = sum(1.0 / o for o in odds)
    stakes = [round(budget_eur * (1.0 / o) / implied, 2) for o in odds]
    guaranteed_return = round(budget_eur / implied, 2)
    profit = round(guaranteed_return - budget_eur, 2)
    return stakes, guaranteed_return, profit
