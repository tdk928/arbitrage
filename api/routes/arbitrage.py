from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker

from scraper.db import get_engine, init_db
from scraper.models import ArbitrageOpportunity, Match, ScrapeRun, Team
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
            triggered_by="api",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/opportunities")
def get_opportunities(
    run_id: Optional[int] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if run_id is None:
        last_run = db.query(ScrapeRun).order_by(ScrapeRun.id.desc()).first()
        if not last_run:
            return {"run_id": None, "opportunities": []}
        run_id = last_run.id

    opps = (
        db.query(ArbitrageOpportunity)
        .filter(ArbitrageOpportunity.scrape_run_id == run_id)
        .order_by(ArbitrageOpportunity.margin_pct.desc())
        .limit(limit)
        .all()
    )
    results = []
    for opp in opps:
        match = db.get(Match, opp.match_id)
        home = db.get(Team, match.home_team_id).name
        away = db.get(Team, match.away_team_id).name
        results.append(
            {
                "match": f"{home} vs {away}",
                "kickoff_utc": match.kickoff_utc.isoformat(),
                "market_type_id": opp.market_type_id,
                "margin_pct": float(opp.margin_pct),
                "legs": opp.legs,
            }
        )
    return {"run_id": run_id, "opportunities": results}
