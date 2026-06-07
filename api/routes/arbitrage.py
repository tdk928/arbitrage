from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker

from scraper.bet_board import build_arbitrage_response, build_match_board
from scraper.db import get_engine, init_db
from scraper.models import ScrapeRun
from scraper.pipeline import run_pipeline
from scraper.seed import seed_session

router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])

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
def run_arbitrage(
    competition: str = Query(default="world-cup-2026"),
    time_window: str = Query(
        default="today_tomorrow",
        pattern="^(next_24h|today_tomorrow|all)$",
    ),
    min_margin: float = Query(default=1.0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    budget: float = Query(default=100.0, ge=1, le=1_000_000),
    seed: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    if seed:
        seed_session(db)
    try:
        return run_pipeline(
            db,
            competition_slug=competition,
            time_window=time_window,
            min_margin=min_margin,
            limit=limit,
            budget_eur=budget,
            triggered_by="api",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/opportunities")
def get_opportunities(
    run_id: Optional[int] = Query(default=None),
    min_margin: float = Query(default=1.0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    budget: float = Query(default=100.0, ge=1, le=1_000_000),
    db: Session = Depends(get_db),
):
    """Arbitrage bets only from latest scrape (no re-scrape, no odds dump)."""
    if run_id is None:
        last_run = db.query(ScrapeRun).order_by(ScrapeRun.id.desc()).first()
        if not last_run:
            return {
                "run_id": None,
                "budget_eur": budget,
                "min_margin_pct": min_margin,
                "count": 0,
                "bets": [],
                "message": "No scrape runs yet.",
            }
        run_id = last_run.id
        scraped_at = (last_run.finished_at or last_run.started_at).isoformat()
    else:
        last_run = db.get(ScrapeRun, run_id)
        scraped_at = (
            (last_run.finished_at or last_run.started_at).isoformat() if last_run else ""
        )

    return build_arbitrage_response(
        db,
        run_id=run_id,
        scraped_at=scraped_at,
        budget_eur=budget,
        min_margin_pct=min_margin,
        limit=limit,
    )


@router.get("/board")
def get_board(
    run_id: Optional[int] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Debug: raw odds grid per site (not arbitrage)."""
    if run_id is None:
        last_run = db.query(ScrapeRun).order_by(ScrapeRun.id.desc()).first()
        if not last_run:
            return {"run_id": None, "matches": []}
        run_id = last_run.id
    return {"run_id": run_id, "matches": build_match_board(db, run_id, limit=limit)}
