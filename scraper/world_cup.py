from __future__ import annotations

"""World Cup 2026 — scrape all listed fixtures from 6 bookmakers, store odds, find arbs."""

from typing import Any

from sqlalchemy.orm import Session

from scraper.pipeline import run_pipeline

WORLD_CUP_SLUG = "world-cup-2026"
WORLD_CUP_TIME_WINDOW = "world_cup"

# Search terms to discover all EGT (winbet/inbet) World Cup fixtures
WC_EGT_SEARCH_TERMS = [
    "Mexico",
    "South Africa",
    "Korea",
    "Czech",
    "Canada",
    "Bosnia",
    "USA",
    "Paraguay",
    "Qatar",
    "Switzerland",
    "Brazil",
    "Morocco",
    "Haiti",
    "Scotland",
    "Australia",
    "Turkey",
    "Germany",
    "Netherlands",
    "Japan",
    "France",
    "Spain",
    "England",
    "Argentina",
    "Portugal",
    "Belgium",
    "Croatia",
    "Uruguay",
    "Colombia",
    "Ecuador",
    "Chile",
    "Italy",
    "Poland",
    "Serbia",
    "Denmark",
    "Sweden",
    "Norway",
    "Austria",
    "Ukraine",
    "Wales",
    "Iran",
    "Saudi",
    "Senegal",
    "Ghana",
    "Cameroon",
    "Tunisia",
    "Egypt",
    "Costa Rica",
    "Panama",
    "Jamaica",
    "Curacao",
]


def run_world_cup_pipeline(
    session: Session,
    min_margin: float = 1.0,
    limit: int = 10,
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
        triggered_by=triggered_by,
    )
