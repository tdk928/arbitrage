from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from scraper.models_v3 import ArbitrageAudit, ArbitrageTop10Current


def _normalize_line(line: Optional[str]) -> str:
    return line or ""


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


def audit_row_to_dict(row: ArbitrageAudit, rank: int) -> dict[str, Any]:
    captured_at = row.captured_at
    return {
        "rank": rank,
        "event_key": row.event_key,
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
        "captured_at": captured_at.isoformat() if captured_at else None,
        "scrape_date": captured_at.date().isoformat() if captured_at else None,
        "scrape_time": captured_at.strftime("%H:%M:%S") if captured_at else None,
        "legs": row.legs,
    }


def fetch_audit_top20(session: Session) -> list[dict[str, Any]]:
    rows = (
        session.query(ArbitrageAudit)
        .order_by(ArbitrageAudit.margin_pct.desc(), ArbitrageAudit.id.asc())
        .limit(20)
        .all()
    )
    return [audit_row_to_dict(row, rank) for rank, row in enumerate(rows, start=1)]


def delete_audit_entry(
    session: Session,
    *,
    run_id: int,
    rule_slug: str,
    home_team: str,
    away_team: str,
    line: Optional[str],
) -> bool:
    row = (
        session.query(ArbitrageAudit)
        .filter(
            ArbitrageAudit.scrape_run_id == run_id,
            ArbitrageAudit.rule_slug == rule_slug,
            ArbitrageAudit.home_team == home_team,
            ArbitrageAudit.away_team == away_team,
            func.coalesce(ArbitrageAudit.line, "") == _normalize_line(line),
        )
        .one_or_none()
    )
    if row is None:
        return False

    session.delete(row)
    session.commit()
    return True


def delete_top10_rank(session: Session, rank: int) -> bool:
    row = session.get(ArbitrageTop10Current, rank)
    if row is None:
        return False

    session.delete(row)
    session.commit()
    return True
