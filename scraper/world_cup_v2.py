from __future__ import annotations

"""World Cup 2026 — v2 all-markets pipeline (EGT + Altenar + efbet)."""

from typing import Any

from sqlalchemy.orm import Session

from scraper.v2.pipeline import run_pipeline_v2

WORLD_CUP_SLUG = "world-cup-2026"
WORLD_CUP_TIME_WINDOW = "world_cup"


def run_world_cup_pipeline_v2(
    session: Session,
    min_margin: float = 1.0,
    limit: int = 10,
    budget_eur: float = 100.0,
    triggered_by: str = "cli",
) -> dict[str, Any]:
    """
    Scrape all markets from efbet, winbet, inbet, palmsbet;
    canonical-match across bookmakers; compute arbitrage.
    """
    return run_pipeline_v2(
        session,
        competition_slug=WORLD_CUP_SLUG,
        time_window=WORLD_CUP_TIME_WINDOW,
        min_margin=min_margin,
        limit=limit,
        budget_eur=budget_eur,
        triggered_by=triggered_by,
    )
