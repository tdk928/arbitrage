from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker

from scraper.db import get_engine, init_db
from scraper.models_v3 import MarketRuleSet, MarketRuleSiteMatch
from scraper.v3.pipeline import run_pipeline_v3
from scraper.v3.response import fetch_top10_current
from scraper.v3.seed_rules import seed_all_rules

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


def _rule_to_dict(rule: MarketRuleSet, include_sites: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": rule.id,
        "slug": rule.slug,
        "label": rule.label,
        "description": rule.description,
        "outcome_roles": rule.outcome_roles,
        "scope": rule.scope,
        "line_filter": rule.line_filter,
        "is_active": rule.is_active,
    }
    if include_sites:
        out["site_matches"] = [_site_to_dict(sm) for sm in rule.site_matches]
    return out


def _site_to_dict(sm: MarketRuleSiteMatch) -> dict[str, Any]:
    return {
        "id": sm.id,
        "rule_set_id": sm.rule_set_id,
        "bookmaker_slug": sm.bookmaker_slug,
        "platform": sm.platform,
        "ui_label": sm.ui_label,
        "match_criteria": sm.match_criteria,
        "priority": sm.priority,
        "is_active": sm.is_active,
        "notes": sm.notes,
    }


@router.get("/rules")
def list_rules(
    slug: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(MarketRuleSet).filter(MarketRuleSet.is_active.is_(True))
    if slug:
        q = q.filter(MarketRuleSet.slug == slug)
    rules = q.order_by(MarketRuleSet.id).all()
    return {"count": len(rules), "rules": [_rule_to_dict(r) for r in rules]}


@router.get("/rules/{slug}/sites")
def list_rule_sites(slug: str, db: Session = Depends(get_db)):
    rule = db.query(MarketRuleSet).filter(MarketRuleSet.slug == slug).one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule not found: {slug}")
    sites = (
        db.query(MarketRuleSiteMatch)
        .filter(MarketRuleSiteMatch.rule_set_id == rule.id)
        .order_by(MarketRuleSiteMatch.bookmaker_slug)
        .all()
    )
    return {
        "rule": _rule_to_dict(rule, include_sites=False),
        "site_matches": [_site_to_dict(s) for s in sites],
    }


@router.post("/rules/seed")
def seed_rules(db: Session = Depends(get_db)):
    rules = seed_all_rules(db)
    db.commit()
    return {
        "status": "ok",
        "seeded": [r.slug for r in rules],
        "rules": [_rule_to_dict(r) for r in rules],
    }


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
def get_top10(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return fetch_top10_current(db)
