from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from scraper.arbitrage import allocate_stakes
from scraper.models import ArbitrageOpportunity, Bookmaker, MarketType, Match, OddsSnapshot, Team

PICK_LABEL = {
    ("MATCH_1X2", "1"): "1",
    ("MATCH_1X2", "X"): "X",
    ("MATCH_1X2", "2"): "2",
    ("GOALS_OU_25", "Over"): "Over 2.5",
    ("GOALS_OU_25", "Under"): "Under 2.5",
    ("CORNERS_OU_85", "Over"): "Over 8.5 corners",
    ("CORNERS_OU_85", "Under"): "Under 8.5 corners",
    ("CORNERS_OU_95", "Over"): "Over 9.5 corners",
    ("CORNERS_OU_95", "Under"): "Under 9.5 corners",
}

BET_TYPE = {
    "MATCH_1X2": "1X2",
    "GOALS_OU_25": "Over/Under 2.5",
    "CORNERS_OU_85": "Over/Under 8.5 corners",
    "CORNERS_OU_95": "Over/Under 9.5 corners",
}


def format_opportunity(
    session: Session,
    opp: ArbitrageOpportunity,
    market_code: str,
    budget_eur: float = 100.0,
) -> dict[str, Any]:
    match = session.get(Match, opp.match_id)
    home = session.get(Team, match.home_team_id).name
    away = session.get(Team, match.away_team_id).name

    odds = [float(leg["odd"]) for leg in opp.legs or []]
    stakes, guaranteed_return, profit = allocate_stakes(budget_eur, odds)

    legs = []
    for leg, stake in zip(opp.legs or [], stakes):
        outcome = leg.get("outcome", "")
        legs.append(
            {
                "site": leg.get("bookmaker", ""),
                "pick": PICK_LABEL.get((market_code, outcome), outcome),
                "odd": float(leg.get("odd")),
                "stake_eur": stake,
            }
        )

    return {
        "match": f"{home} vs {away}",
        "date": match.kickoff_utc.isoformat(),
        "bet": BET_TYPE.get(market_code, market_code),
        "arbitrage_pct": float(opp.margin_pct),
        "legs": legs,
        "budget_eur": budget_eur,
        "guaranteed_return_eur": guaranteed_return,
        "profit_eur": profit,
    }


def build_arbitrage_response(
    session: Session,
    run_id: int,
    scraped_at: str,
    budget_eur: float,
    min_margin_pct: float,
    limit: int,
) -> dict[str, Any]:
    market_types = {m.id: m.code for m in session.query(MarketType).all()}
    opps = (
        session.query(ArbitrageOpportunity)
        .filter(ArbitrageOpportunity.scrape_run_id == run_id)
        .filter(ArbitrageOpportunity.margin_pct >= min_margin_pct)
        .order_by(ArbitrageOpportunity.margin_pct.desc())
        .limit(limit)
        .all()
    )
    bets = [
        format_opportunity(session, opp, market_types.get(opp.market_type_id, ""), budget_eur)
        for opp in opps
    ]
    result: dict[str, Any] = {
        "run_id": run_id,
        "scraped_at": scraped_at,
        "budget_eur": budget_eur,
        "min_margin_pct": min_margin_pct,
        "count": len(bets),
        "bets": bets,
    }
    if not bets:
        result["message"] = f"No arbitrage opportunities at or above {min_margin_pct}% margin."
    return result


# --- debug board (GET /board only) ---

OUTCOME_FIELD = {
    ("MATCH_1X2", "1"): "home_1",
    ("MATCH_1X2", "X"): "draw_x",
    ("MATCH_1X2", "2"): "away_2",
    ("GOALS_OU_25", "Over"): "over_2_5",
    ("GOALS_OU_25", "Under"): "under_2_5",
    ("CORNERS_OU_85", "Over"): "over_corners_8_5",
    ("CORNERS_OU_85", "Under"): "under_corners_8_5",
    ("CORNERS_OU_95", "Over"): "over_corners_9_5",
    ("CORNERS_OU_95", "Under"): "under_corners_9_5",
}


def build_match_board(session: Session, run_id: int, limit: int = 10) -> list[dict[str, Any]]:
    market_types = {m.id: m.code for m in session.query(MarketType).all()}
    bookmakers = {b.id: b.slug for b in session.query(Bookmaker).all()}

    snapshots = (
        session.query(OddsSnapshot)
        .filter(OddsSnapshot.scrape_run_id == run_id, OddsSnapshot.success.is_(True))
        .all()
    )

    by_match: dict[int, dict[str, dict[str, float | None]]] = {}
    site_count: dict[int, set[str]] = {}

    for snap in snapshots:
        code = market_types.get(snap.market_type_id)
        site = bookmakers.get(snap.bookmaker_id)
        if not code or not site:
            continue
        site_count.setdefault(snap.match_id, set()).add(site)
        row = by_match.setdefault(snap.match_id, {}).setdefault(site, _empty_site_odds())
        for outcome in snap.outcomes or []:
            name = outcome.get("name")
            odd = outcome.get("odd")
            field = OUTCOME_FIELD.get((code, name))
            if field and odd:
                row[field] = float(odd)

    match_ids = sorted(
        by_match.keys(),
        key=lambda mid: (-len(site_count.get(mid, set())), mid),
    )[:limit]

    board = []
    for mid in match_ids:
        match = session.get(Match, mid)
        home = session.get(Team, match.home_team_id).name
        away = session.get(Team, match.away_team_id).name
        board.append(
            {
                "match": f"{home} vs {away}",
                "kickoff": match.kickoff_utc.isoformat(),
                "sites_count": len(by_match[mid]),
                "odds_by_site": by_match[mid],
            }
        )
    return board


def _empty_site_odds() -> dict[str, float | None]:
    return {
        "home_1": None,
        "draw_x": None,
        "away_2": None,
        "over_2_5": None,
        "under_2_5": None,
        "over_corners_8_5": None,
        "under_corners_8_5": None,
        "over_corners_9_5": None,
        "under_corners_9_5": None,
    }
