from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from scraper.arbitrage import compute_arbitrage, rank_opportunities
from scraper.matcher import group_fixtures, pick_canonical
from scraper.models import (
    ArbitrageOpportunity,
    Bookmaker,
    Competition,
    CompetitionSource,
    MarketType,
    Match,
    OddsSnapshot,
    ScrapeRun,
    Team,
)
from scraper.normalize import canonical_key, normalize_team
from scraper.platforms.registry import get_scraper
from scraper.time_filter import filter_fixtures
from scraper.types import RawFixture


def run_pipeline(
    session: Session,
    competition_slug: str,
    time_window: str,
    min_margin: float,
    limit: int,
    triggered_by: str = "cli",
) -> dict[str, Any]:
    competition = (
        session.query(Competition).filter(Competition.slug == competition_slug).one_or_none()
    )
    if not competition:
        raise ValueError(f"Competition not found: {competition_slug}")

    run = ScrapeRun(
        competition_slug=competition_slug,
        time_window=time_window,
        status="running",
        triggered_by=triggered_by,
    )
    session.add(run)
    session.flush()

    market_types = {m.code: m for m in session.query(MarketType).all()}
    bookmakers = {b.slug: b for b in session.query(Bookmaker).filter(Bookmaker.is_active).all()}
    sources = (
        session.query(CompetitionSource)
        .filter(CompetitionSource.competition_id == competition.id)
        .all()
    )

    all_fixtures: list[RawFixture] = []
    errors: list[str] = []
    fixtures_by_bookmaker: dict[str, int] = {}

    for src in sources:
        bm = session.get(Bookmaker, src.bookmaker_id)
        if not bm or not bm.is_active:
            continue
        try:
            scraper = get_scraper(bm.slug)
            fixtures = scraper.list_fixtures(src.discovery_config or {})
            filtered = filter_fixtures(fixtures, time_window)
            fixtures_by_bookmaker[bm.slug] = len(filtered)
            all_fixtures.extend(filtered)
        except Exception as exc:
            fixtures_by_bookmaker[bm.slug] = 0
            errors.append(f"{bm.slug} list: {exc}")

    groups = group_fixtures(all_fixtures)
    match_by_id: dict[int, Match] = {}

    for group in groups:
        if not group:
            continue
        home, away, _ = pick_canonical(group)
        kickoff = min(g.kickoff_utc for g in group)
        ckey = canonical_key(home, away, kickoff)

        home_team = _get_or_create_team(session, home)
        away_team = _get_or_create_team(session, away)

        match = (
            session.query(Match)
            .filter(
                Match.competition_id == competition.id,
                Match.canonical_key == ckey,
            )
            .one_or_none()
        )
        external_ids: dict[str, str] = {}
        if match:
            external_ids = dict(match.external_ids or {})
        else:
            match = Match(
                competition_id=competition.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                kickoff_utc=kickoff,
                canonical_key=ckey,
                external_ids={},
            )
            session.add(match)
            session.flush()

        for fx in group:
            external_ids[fx.bookmaker_slug] = fx.external_id
        match.external_ids = external_ids
        match_by_id[match.id] = match

    odds_by_match_market: dict[tuple[int, str], dict[str, list]] = {}
    odds_by_bookmaker: dict[str, int] = defaultdict(int)

    for src in sources:
        bm = session.get(Bookmaker, src.bookmaker_id)
        if not bm:
            continue
        scraper = get_scraper(bm.slug)
        for match in match_by_id.values():
            ext_id = (match.external_ids or {}).get(bm.slug)
            if not ext_id:
                continue
            try:
                markets = scraper.fetch_markets(ext_id, src.discovery_config or {})
                if not markets:
                    continue
                for mkt in markets:
                    mt = market_types.get(mkt.market_code)
                    if not mt:
                        continue
                    outcomes = [{"name": o.name, "odd": o.odd} for o in mkt.outcomes]
                    session.add(
                        OddsSnapshot(
                            scrape_run_id=run.id,
                            match_id=match.id,
                            bookmaker_id=bm.id,
                            market_type_id=mt.id,
                            outcomes=outcomes,
                            success=True,
                        )
                    )
                    odds_by_bookmaker[bm.slug] += 1
                    key = (match.id, mkt.market_code)
                    if key not in odds_by_match_market:
                        odds_by_match_market[key] = {}
                    odds_by_match_market[key][bm.slug] = outcomes
            except Exception as exc:
                session.add(
                    OddsSnapshot(
                        scrape_run_id=run.id,
                        match_id=match.id,
                        bookmaker_id=bm.id,
                        market_type_id=market_types["MATCH_1X2"].id,
                        outcomes=[],
                        success=False,
                        error_message=str(exc),
                    )
                )
                errors.append(f"{bm.slug} odds match {match.id}: {exc}")

    opportunities = []
    for (match_id, market_code), bm_odds in odds_by_match_market.items():
        result = compute_arbitrage(market_code, bm_odds, min_margin=min_margin)
        if not result:
            continue
        mt = market_types[market_code]
        opp = ArbitrageOpportunity(
            scrape_run_id=run.id,
            match_id=match_id,
            market_type_id=mt.id,
            margin_pct=result.margin_pct,
            implied_total=result.implied_total,
            legs=result.legs,
            bookmaker_count=result.bookmaker_count,
        )
        session.add(opp)
        match = match_by_id[match_id]
        opportunities.append((match, mt, result))

    ranked = rank_opportunities([r for _, _, r in opportunities], limit=limit)

    run.status = "partial" if errors else "success"
    if errors and not opportunities:
        run.status = "failed"
    run.finished_at = datetime.now(tz=timezone.utc)
    run.notes = "; ".join(errors[:20]) if errors else None
    session.commit()

    bookmaker_coverage = _bookmaker_coverage(session, match_by_id)
    total_opps = (
        session.query(func.count(ArbitrageOpportunity.id))
        .filter(ArbitrageOpportunity.scrape_run_id == run.id)
        .scalar()
    )

    return format_response(
        session,
        run,
        ranked,
        match_by_id,
        market_types,
        limit,
        stats={
            "fixtures_by_bookmaker": fixtures_by_bookmaker,
            "matches_linked": len(match_by_id),
            "odds_snapshots_by_bookmaker": dict(odds_by_bookmaker),
            "odds_snapshots_total": sum(odds_by_bookmaker.values()),
            "opportunities_total": total_opps,
            "bookmaker_coverage": bookmaker_coverage,
        },
    )


def _bookmaker_coverage(session: Session, match_by_id: dict[int, Match]) -> list[dict[str, Any]]:
    """How many bookmakers each linked match has."""
    coverage: list[dict[str, Any]] = []
    for match in sorted(match_by_id.values(), key=lambda m: m.kickoff_utc):
        home = session.get(Team, match.home_team_id).name
        away = session.get(Team, match.away_team_id).name
        bms = sorted((match.external_ids or {}).keys())
        coverage.append(
            {
                "match": f"{home} vs {away}",
                "kickoff_utc": match.kickoff_utc.isoformat(),
                "bookmaker_count": len(bms),
                "bookmakers": bms,
            }
        )
    return coverage


def _get_or_create_team(session: Session, name: str) -> Team:
    norm = normalize_team(name)
    team = session.query(Team).filter(Team.name_normalized == norm).one_or_none()
    if team:
        return team
    team = Team(name=name, name_normalized=norm)
    session.add(team)
    session.flush()
    return team


def format_response(
    session: Session,
    run: ScrapeRun,
    ranked: list,
    match_by_id: dict[int, Match],
    market_types: dict[str, MarketType],
    limit: int,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    code_by_id = {m.id: m.code for m in market_types.values()}
    opps_db = (
        session.query(ArbitrageOpportunity)
        .filter(ArbitrageOpportunity.scrape_run_id == run.id)
        .order_by(ArbitrageOpportunity.margin_pct.desc())
        .limit(limit)
        .all()
    )
    out_opps = []
    for opp in opps_db:
        match = session.get(Match, opp.match_id)
        home = session.get(Team, match.home_team_id).name
        away = session.get(Team, match.away_team_id).name
        out_opps.append(
            {
                "match": f"{home} vs {away}",
                "kickoff_utc": match.kickoff_utc.isoformat(),
                "market": code_by_id.get(opp.market_type_id, ""),
                "margin_pct": float(opp.margin_pct),
                "implied_total": float(opp.implied_total),
                "bookmaker_count": opp.bookmaker_count,
                "legs": opp.legs,
            }
        )

    result: dict[str, Any] = {
        "run_id": run.id,
        "scraped_at": (run.finished_at or run.started_at).isoformat(),
        "time_window": run.time_window,
        "competition": run.competition_slug,
        "status": run.status,
        "errors": run.notes,
        "opportunities": out_opps,
    }
    if stats:
        result["stats"] = stats
    return result
