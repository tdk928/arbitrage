from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from api.routes.auth import require_admin, require_subscribed_client_or_admin
from scraper.db import get_engine, init_db
from scraper.models_auth import User
from scraper.v3.pipeline import run_pipeline_v3
from scraper.v3.response import (
    delete_audit_entry,
    delete_top10_rank,
    fetch_audit_top20,
    fetch_top10_current,
)

router = APIRouter(prefix="/arbitrage/v3", tags=["arbitrage-v3"])

_engine = None
_SessionLocal = None


def _get_session_factory():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        init_db()
        _engine = get_engine()
        _SessionLocal = sessionmaker(bind=_engine)
    return _SessionLocal


def get_db():
    SessionLocal = _get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/run")
def run_arbitrage_v3(
    competition: str = Query(default="world-cup-2026"),
    time_window: str = Query(
        default="world_cup",
        pattern="^(next_24h|today_tomorrow|all|world_cup)$",
    ),
    min_margin: float = Query(default=1.0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    rules: Optional[list[str]] = Query(default=None),
    _: User = Depends(require_subscribed_client_or_admin),
    db: Session = Depends(get_db),
):
    try:
        return run_pipeline_v3(
            db,
            competition_slug=competition,
            time_window=time_window,
            triggered_by="api",
            rule_slugs=rules,
            min_margin=min_margin,
            top_limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/top10")
def get_top10(
    _: User = Depends(require_subscribed_client_or_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return fetch_top10_current(db)


@router.get("/audit")
def get_audit_top20(
    _: User = Depends(require_subscribed_client_or_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return fetch_audit_top20(db)


class AuditDeleteRequest(BaseModel):
    run_id: int
    rule_slug: str
    home_team: str
    away_team: str
    line: Optional[str] = None


@router.delete("/audit", status_code=status.HTTP_204_NO_CONTENT)
def delete_audit(
    body: AuditDeleteRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    deleted = delete_audit_entry(
        db,
        run_id=body.run_id,
        rule_slug=body.rule_slug,
        home_team=body.home_team,
        away_team=body.away_team,
        line=body.line,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit entry not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/top10/{rank}", status_code=status.HTTP_204_NO_CONTENT)
def delete_top10(
    rank: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    deleted = delete_top10_rank(db, rank)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Top 10 entry not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
