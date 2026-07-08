from __future__ import annotations

from typing import Any

from scraper.v2.types import ParsedMarket
from scraper.v3.criteria import criteria_match


def select_odds_rows_from_markets(
    parsed_markets: list[ParsedMarket],
    *,
    rule_id: int,
    rule_line_filter: str,
    match_criteria: dict[str, Any],
    seen_odds_keys: set[tuple[int, int, int, str]] | None = None,
    match_id: int = 1,
    bookmaker_id: int = 1,
) -> list[dict[str, Any]]:
    """
    Mirror of scraper/v3/pipeline.py odds selection (lines 173-206).
    Used by regression tests to verify rule filtering is unchanged.
    """
    seen = seen_odds_keys if seen_odds_keys is not None else set()
    rows: list[dict[str, Any]] = []

    for parsed in parsed_markets:
        if not criteria_match(match_criteria, parsed):
            continue
        needs_line = rule_line_filter == "half_only"
        if needs_line and not parsed.line:
            continue
        line = str(parsed.line) if parsed.line else ""
        odds_key = (rule_id, match_id, bookmaker_id, line)
        if odds_key in seen:
            continue
        seen.add(odds_key)
        rows.append(
            {
                "rule_id": rule_id,
                "match_id": match_id,
                "bookmaker_id": bookmaker_id,
                "line": line,
                "market_name": parsed.market_name,
                "outcomes": [
                    {"role": o.role, "name": o.name, "odd": o.odd} for o in parsed.outcomes
                ],
            }
        )

    return rows
