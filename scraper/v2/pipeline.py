from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from scraper.arbitrage import allocate_stakes
from scraper.matcher import group_fixtures, pick_canonical
from scraper.models import Bookmaker, Competition, CompetitionSource, Match, Team
from scraper.models_v2 import (
    ArbitrageOpportunityV2,
    CanonicalMarketV2,
    OddsSnapshotV2,
    RawMarketV2,
    ScrapeRunV2,
)
from scraper.normalize import canonical_key, normalize_team
from scraper.platforms.registry import get_scraper
from scraper.time_filter import filter_fixtures
from scraper.types import RawFixture
from scraper.v2.arbitrage import compute_arbitrage_v2, rank_opportunities_v2
from scraper.v2.canonical import ARB_ELIGIBLE_FAMILIES, build_canonical_key
from scraper.v2.raw_fetchers import fetch_all_markets_for_event
from scraper.v2.types import ParsedMarket, V2_BOOKMAKER_SLUGS


def _get_or_create_team(session: Session, name: str) -> Team:
    norm = normalize_team(name)
    team = session.query(Team).filter(Team.name_normalized == norm).one_or_none()
    if team:
        return team
    team = Team(name=name, name_normalized=norm)
    session.add(team)
    session.flush()
    return team


def _get_or_create_canonical(
    session: Session,
    parsed: ParsedMarket,
) -> CanonicalMarketV2 | None:
    if not parsed.mapped or len(parsed.outcomes) < 2:
        return None

    roles = list(parsed.outcome_roles)
    key = build_canonical_key(
        parsed.family,
        parsed.period,
        parsed.scope,
        parsed.line,
        parsed.outcome_roles,
        market_name=parsed.market_name,
    )

    canonical = (
        session.query(CanonicalMarketV2)
        .filter(CanonicalMarketV2.canonical_key == key)
        .one_or_none()
    )
    if not canonical:
        canonical = CanonicalMarketV2(
            canonical_key=key,
            family=parsed.family,
            period=parsed.period,
            scope=parsed.scope,
            line=parsed.line,
            outcome_roles=roles,
            label=parsed.label,
        )
        session.add(canonical)
        session.flush()
    return canonical


def run_pipeline_v2(
    session: Session,
    competition_slug: str,
    time_window: str,
    min_margin: float,
    limit: int,
    triggered_by: str = "cli",
    budget_eur: float = 100.0,
) -> dict[str, Any]:
    competition = (
        session.query(Competition).filter(Competition.slug == competition_slug).one_or_none()
    )
    if not competition:
        raise ValueError(f"Competition not found: {competition_slug}")

    run = ScrapeRunV2(
        competition_slug=competition_slug,
        time_window=time_window,
        status="running",
        triggered_by=triggered_by,
        stats={},
    )
    session.add(run)
    session.flush()

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
        if not bm or not bm.is_active or bm.slug not in V2_BOOKMAKER_SLUGS:
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

    raw_count_by_bm: dict[str, int] = defaultdict(int)
    mapped_count_by_bm: dict[str, int] = defaultdict(int)
    odds_by_match_canonical: dict[tuple[int, int], dict[str, list]] = defaultdict(dict)
    canonical_meta: dict[int, CanonicalMarketV2] = {}
    snapshot_buffer: dict[tuple[int, int, int], list] = {}

    for src in sources:
        bm = session.get(Bookmaker, src.bookmaker_id)
        if not bm or bm.slug not in V2_BOOKMAKER_SLUGS:
            continue

        for match in match_by_id.values():
            ext_id = (match.external_ids or {}).get(bm.slug)
            if not ext_id:
                continue
            try:
                parsed_markets = fetch_all_markets_for_event(
                    bm.slug,
                    bm.platform,
                    ext_id,
                    src.discovery_config or {},
                )
                for parsed in parsed_markets:
                    raw_count_by_bm[bm.slug] += 1
                    canonical = _get_or_create_canonical(session, parsed)
                    outcomes_json = [
                        {"role": o.role, "name": o.name, "odd": o.odd}
                        for o in parsed.outcomes
                    ]
                    session.add(
                        RawMarketV2(
                            scrape_run_id=run.id,
                            match_id=match.id,
                            bookmaker_id=bm.id,
                            canonical_market_id=canonical.id if canonical else None,
                            external_market_id=parsed.external_id,
                            market_name=parsed.market_name,
                            provider_template=parsed.provider_template,
                            specifiers=parsed.specifiers,
                            outcomes=outcomes_json,
                            raw_payload=parsed.raw_payload,
                            mapped=canonical is not None,
                        )
                    )
                    if not canonical:
                        continue
                    mapped_count_by_bm[bm.slug] += 1
                    canonical_meta[canonical.id] = canonical

                    snapshot_buffer[(match.id, bm.id, canonical.id)] = outcomes_json
                    key = (match.id, canonical.id)
                    odds_by_match_canonical[key][bm.slug] = outcomes_json

            except Exception as exc:
                errors.append(f"{bm.slug} markets match {match.id}: {exc}")

    for (match_id, bookmaker_id, canonical_id), outcomes_json in snapshot_buffer.items():
        session.add(
            OddsSnapshotV2(
                scrape_run_id=run.id,
                match_id=match_id,
                bookmaker_id=bookmaker_id,
                canonical_market_id=canonical_id,
                outcomes=outcomes_json,
            )
        )

    opportunities: list[tuple[int, CanonicalMarketV2, Any]] = []

    for (match_id, canonical_id), bm_odds in odds_by_match_canonical.items():
        if len(bm_odds) < 2:
            continue
        canonical = canonical_meta.get(canonical_id)
        if not canonical or canonical.family not in ARB_ELIGIBLE_FAMILIES:
            continue

        # Require aligned outcome roles across all bookmakers present
        expected_roles = canonical.outcome_roles
        aligned: dict[str, list] = {}
        for bm_slug, outcomes in bm_odds.items():
            roles = {o["role"] for o in outcomes}
            if set(expected_roles).issubset(roles):
                aligned[bm_slug] = outcomes

        if len(aligned) < 2:
            continue

        result = compute_arbitrage_v2(expected_roles, aligned, min_margin=min_margin)
        if not result:
            continue

        session.add(
            ArbitrageOpportunityV2(
                scrape_run_id=run.id,
                match_id=match_id,
                canonical_market_id=canonical_id,
                margin_pct=result.margin_pct,
                implied_total=result.implied_total,
                legs=result.legs,
                bookmaker_count=result.bookmaker_count,
            )
        )
        result.canonical_market_id = canonical_id
        result.market_label = canonical.label
        result.family = canonical.family
        opportunities.append((match_id, canonical, result))

    ranked = rank_opportunities_v2([r for _, _, r in opportunities], limit=limit)

    matched_pairs = sum(
        1 for bm_odds in odds_by_match_canonical.values() if len(bm_odds) >= 2
    )

    run.stats = {
        "fixtures_by_bookmaker": fixtures_by_bookmaker,
        "matches_linked": len(match_by_id),
        "raw_markets_by_bookmaker": dict(raw_count_by_bm),
        "mapped_markets_by_bookmaker": dict(mapped_count_by_bm),
        "cross_bookmaker_market_pairs": matched_pairs,
        "pipeline_version": "v2",
        "bookmakers": sorted(V2_BOOKMAKER_SLUGS),
    }
    run.status = "partial" if errors else "success"
    if errors and not opportunities:
        run.status = "failed"
    run.finished_at = datetime.now(tz=timezone.utc)
    run.notes = "; ".join(errors[:20]) if errors else None
    session.commit()

    return format_response_v2(
        session,
        run,
        ranked=ranked,
        limit=limit,
        min_margin=min_margin,
        budget_eur=budget_eur,
    )


def format_response_v2(
    session: Session,
    run: ScrapeRunV2,
    ranked: list,
    limit: int,
    min_margin: float,
    budget_eur: float,
) -> dict[str, Any]:
    from scraper.models import Team

    opp_rows = (
        session.query(ArbitrageOpportunityV2, Match, CanonicalMarketV2)
        .join(Match, Match.id == ArbitrageOpportunityV2.match_id)
        .join(
            CanonicalMarketV2,
            CanonicalMarketV2.id == ArbitrageOpportunityV2.canonical_market_id,
        )
        .filter(ArbitrageOpportunityV2.scrape_run_id == run.id)
        .order_by(ArbitrageOpportunityV2.margin_pct.desc())
        .limit(limit)
        .all()
    )

    bets = []
    for opp, match, canonical in opp_rows:
        home = session.get(Team, match.home_team_id)
        away = session.get(Team, match.away_team_id)
        odds = [leg["odd"] for leg in opp.legs]
        stakes, guaranteed, profit = allocate_stakes(budget_eur, odds)
        legs_out = []
        for leg, stake in zip(opp.legs, stakes):
            legs_out.append({**leg, "stake_eur": stake})
        bets.append(
            {
                "match": f"{home.name if home else '?'} vs {away.name if away else '?'}",
                "kickoff_utc": match.kickoff_utc.isoformat(),
                "market": canonical.label,
                "family": canonical.family,
                "margin_pct": float(opp.margin_pct),
                "bookmaker_count": opp.bookmaker_count,
                "legs": legs_out,
                "budget_eur": budget_eur,
                "guaranteed_return_eur": guaranteed,
                "profit_eur": profit,
            }
        )

    return {
        "run_id": run.id,
        "pipeline_version": "v2",
        "scraped_at": (run.finished_at or run.started_at).isoformat(),
        "time_window": run.time_window,
        "competition": run.competition_slug,
        "status": run.status,
        "errors": run.notes,
        "stats": run.stats,
        "min_margin_pct": min_margin,
        "count": len(bets),
        "bets": bets,
    }
