from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker

from scraper.db import get_engine, init_db
from scraper.db_init_v2 import init_db_v2
from scraper.models_v2 import ScrapeRunV2
from scraper.seed import seed_session
from scraper.v2.pipeline import run_pipeline_v2
from scraper.v2.response import build_markets_debug, build_opportunities_response
from scraper.world_cup_v2 import run_world_cup_pipeline_v2

router = APIRouter(prefix="/arbitrage/v2", tags=["arbitrage-v2"])

_engine = None
_SessionLocal = None


def _get_session_factory():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        init_db()
        init_db_v2()
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
def run_arbitrage_v2(
    competition: str = Query(default="world-cup-2026"),
    time_window: str = Query(
        default="world_cup",
        pattern="^(next_24h|today_tomorrow|all|world_cup)$",
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
        return run_pipeline_v2(
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


@router.post("/world-cup/run")
def run_world_cup_v2(
    min_margin: float = Query(default=1.0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    budget: float = Query(default=100.0, ge=1, le=1_000_000),
    seed: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    if seed:
        seed_session(db)
    try:
        return run_world_cup_pipeline_v2(
            db,
            min_margin=min_margin,
            limit=limit,
            budget_eur=budget,
            triggered_by="api",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/opportunities")
def get_opportunities_v2(
    run_id: Optional[int] = Query(default=None),
    min_margin: float = Query(default=1.0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    budget: float = Query(default=100.0, ge=1, le=1_000_000),
    db: Session = Depends(get_db),
):
    if run_id is None:
        last_run = db.query(ScrapeRunV2).order_by(ScrapeRunV2.id.desc()).first()
        if not last_run:
            return {
                "run_id": None,
                "pipeline_version": "v2",
                "count": 0,
                "bets": [],
                "message": "No v2 scrape runs yet.",
            }
        run_id = last_run.id
        scraped_at = (last_run.finished_at or last_run.started_at).isoformat()
    else:
        last_run = db.get(ScrapeRunV2, run_id)
        scraped_at = (
            (last_run.finished_at or last_run.started_at).isoformat() if last_run else ""
        )

    return build_opportunities_response(
        db,
        run_id=run_id,
        scraped_at=scraped_at,
        min_margin=min_margin,
        limit=limit,
        budget_eur=budget,
    )


@router.get("/markets")
def get_markets_debug_v2(
    run_id: Optional[int] = Query(default=None),
    match_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if run_id is None:
        last_run = db.query(ScrapeRunV2).order_by(ScrapeRunV2.id.desc()).first()
        if not last_run:
            return {"run_id": None, "raw_markets_sample": [], "cross_bookmaker_markets": []}
        run_id = last_run.id
    return build_markets_debug(db, run_id=run_id, match_id=match_id, limit=limit)
