from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from scraper.models_v3 import ArbitrageTop10Current


def top10_row_to_dict(row: ArbitrageTop10Current) -> dict[str, Any]:
    return {
        "rank": row.rank,
        "run_id": row.scrape_run_id,
        "rule_slug": row.rule_slug,
        "match": f"{row.home_team} vs {row.away_team}",
        "home_team": row.home_team,
        "away_team": row.away_team,
        "market": row.market_label,
        "line": row.line or "",
        "margin_pct": float(row.margin_pct),
        "implied_total": float(row.implied_total),
        "bookmaker_count": row.bookmaker_count,
        "kickoff_utc": row.kickoff_utc.isoformat() if row.kickoff_utc else None,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
        "legs": row.legs,
    }


def fetch_top10_current(session: Session) -> list[dict[str, Any]]:
    rows = (
        session.query(ArbitrageTop10Current)
        .order_by(ArbitrageTop10Current.rank)
        .all()
    )
    return [top10_row_to_dict(row) for row in rows]
