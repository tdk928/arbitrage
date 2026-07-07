from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from scraper.v3.pipeline import run_pipeline_v3

WORLD_CUP_SLUG = "world-cup-2026"
WORLD_CUP_TIME_WINDOW = "world_cup"


def run_world_cup_pipeline_v3(
    session: Session,
    triggered_by: str = "cli",
    rule_slugs: list[str] | None = None,
    min_margin: float = 1.0,
    top_limit: int = 10,
) -> dict[str, Any]:
    return run_pipeline_v3(
        session,
        competition_slug=WORLD_CUP_SLUG,
        time_window=WORLD_CUP_TIME_WINDOW,
        triggered_by=triggered_by,
        rule_slugs=rule_slugs,
        min_margin=min_margin,
        top_limit=top_limit,
    )
