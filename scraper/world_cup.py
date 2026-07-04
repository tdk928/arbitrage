from __future__ import annotations

"""World Cup 2026 — scrape all listed fixtures from 6 bookmakers, store odds, find arbs."""

from typing import Any

from sqlalchemy.orm import Session

from scraper.pipeline import run_pipeline

WORLD_CUP_SLUG = "world-cup-2026"
WORLD_CUP_TIME_WINDOW = "world_cup"

from scraper.wc_constants import WC_EGT_SEARCH_TERMS

def run_world_cup_pipeline(
    session: Session,
    min_margin: float = 1.0,
    limit: int = 10,
    budget_eur: float = 100.0,
    triggered_by: str = "cli",
) -> dict[str, Any]:
    """
    Scrape every World Cup 2026 fixture available on each of the 6 bookmakers,
    persist matches + odds snapshots, and compute arbitrage across all of them.
    """
    return run_pipeline(
        session,
        competition_slug=WORLD_CUP_SLUG,
        time_window=WORLD_CUP_TIME_WINDOW,
        min_margin=min_margin,
        limit=limit,
        budget_eur=budget_eur,
        triggered_by=triggered_by,
    )
