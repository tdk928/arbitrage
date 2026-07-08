from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from scraper.matcher import group_fixtures, pick_canonical
from scraper.models import Bookmaker, Competition, CompetitionSource, Match, Team
from scraper.models_v3 import MarketOddsV3, MarketRuleSet, MarketRuleSiteMatch, ScrapeRunV3
from scraper.normalize import canonical_key, normalize_team
from scraper.platforms.registry import get_scraper
from scraper.time_filter import filter_fixtures
from scraper.types import RawFixture
from scraper.v2.raw_fetchers import (
    clear_fetch_caches,
    fetch_all_markets_for_event,
    get_event_fetch_stats,
)
from scraper.v3.arbitrage import compute_opportunities_v3, persist_top10_and_audit
from scraper.v3.criteria import criteria_match

V3_BOOKMAKER_SLUGS = frozenset({"efbet", "winbet", "inbet", "palmsbet", "8888", "betano"})


def _get_or_create_team(session: Session, name: str) -> Team:
    norm = normalize_team(name)
    team = session.query(Team).filter(Team.name_normalized == norm).one_or_none()
    if team:
        return team
    team = Team(name=name, name_normalized=norm)
    session.add(team)
    session.flush()
    return team


def _link_matches(
    session: Session,
    competition: Competition,
    sources: list[CompetitionSource],
    time_window: str,
) -> tuple[dict[int, Match], dict[str, int], list[str]]:
    all_fixtures: list[RawFixture] = []
    fixtures_by_bookmaker: dict[str, int] = {}
    errors: list[str] = []

    for src in sources:
        bm = session.get(Bookmaker, src.bookmaker_id)
        if not bm or not bm.is_active or bm.slug not in V3_BOOKMAKER_SLUGS:
            continue
        try:
            fixtures = get_scraper(bm.slug).list_fixtures(src.discovery_config or {})
            filtered = filter_fixtures(fixtures, time_window)
            fixtures_by_bookmaker[bm.slug] = len(filtered)
            all_fixtures.extend(filtered)
        except Exception as exc:
            fixtures_by_bookmaker[bm.slug] = 0
            errors.append(f"{bm.slug} list: {exc}")

    match_by_id: dict[int, Match] = {}
    for group in group_fixtures(all_fixtures):
        if not group:
            continue
        home, away, _ = pick_canonical(group)
        kickoff = min(g.kickoff_utc for g in group)
        ckey = canonical_key(home, away, kickoff)

        home_team = _get_or_create_team(session, home)
        away_team = _get_or_create_team(session, away)

        match = (
            session.query(Match)
            .filter(Match.competition_id == competition.id, Match.canonical_key == ckey)
            .one_or_none()
        )
        external_ids: dict[str, str] = dict(match.external_ids or {}) if match else {}
        if not match:
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

    return match_by_id, fixtures_by_bookmaker, errors


def run_pipeline_v3(
    session: Session,
    competition_slug: str,
    time_window: str,
    triggered_by: str = "cli",
    rule_slugs: list[str] | None = None,
    min_margin: float = 1.0,
    top_limit: int = 10,
) -> dict[str, Any]:
    clear_fetch_caches()

    competition = (
        session.query(Competition).filter(Competition.slug == competition_slug).one_or_none()
    )
    if not competition:
        raise ValueError(f"Competition not found: {competition_slug}")

    rules_q = session.query(MarketRuleSet).filter(MarketRuleSet.is_active.is_(True))
    if rule_slugs:
        rules_q = rules_q.filter(MarketRuleSet.slug.in_(rule_slugs))
    rules = rules_q.order_by(MarketRuleSet.id).all()
    if not rules:
        raise ValueError("No active market rules found")

    run = ScrapeRunV3(
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
    source_by_bm: dict[int, CompetitionSource] = {s.bookmaker_id: s for s in sources}

    match_by_id, fixtures_by_bookmaker, errors = _link_matches(
        session, competition, sources, time_window
    )

    odds_count_by_rule: dict[str, int] = defaultdict(int)
    odds_count_by_bm: dict[str, int] = defaultdict(int)
    batch: list[MarketOddsV3] = []
    seen_odds_keys: set[tuple[int, int, int, str]] = set()

    for rule in rules:
        site_rules = {
            sm.bookmaker_slug: sm
            for sm in session.query(MarketRuleSiteMatch)
            .filter(
                MarketRuleSiteMatch.rule_set_id == rule.id,
                MarketRuleSiteMatch.is_active.is_(True),
            )
            .all()
        }

        for match in match_by_id.values():
            for slug, sm in site_rules.items():
                bm = session.query(Bookmaker).filter(Bookmaker.slug == slug).one_or_none()
                if not bm:
                    continue
                ext_id = (match.external_ids or {}).get(slug)
                if not ext_id:
                    continue
                src = source_by_bm.get(bm.id)
                if not src:
                    continue
                try:
                    parsed_markets = fetch_all_markets_for_event(
                        slug,
                        sm.platform,
                        ext_id,
                        src.discovery_config or {},
                    )
                    for parsed in parsed_markets:
                        if not criteria_match(sm.match_criteria, parsed):
                            continue
                        needs_line = rule.line_filter == "half_only"
                        if needs_line and not parsed.line:
                            continue
                        line = str(parsed.line) if parsed.line else ""
                        odds_key = (rule.id, match.id, bm.id, line)
                        if odds_key in seen_odds_keys:
                            continue
                        seen_odds_keys.add(odds_key)
                        outcomes_json = [
                            {"role": o.role, "name": o.name, "odd": o.odd}
                            for o in parsed.outcomes
                        ]
                        batch.append(
                            MarketOddsV3(
                                scrape_run_id=run.id,
                                rule_set_id=rule.id,
                                match_id=match.id,
                                bookmaker_id=bm.id,
                                line=line,
                                market_name=parsed.market_name,
                                external_event_id=str(ext_id),
                                ui_label=sm.ui_label,
                                outcomes=outcomes_json,
                            )
                        )
                        if len(batch) >= 500:
                            session.add_all(batch)
                            session.flush()
                            batch.clear()
                        odds_count_by_rule[rule.slug] += 1
                        odds_count_by_bm[slug] += 1
                except Exception as exc:
                    errors.append(f"{slug} {rule.slug} match {match.id}: {exc}")

    if batch:
        session.add_all(batch)
        session.flush()

    opportunities = compute_opportunities_v3(session, run.id, min_margin=min_margin)
    top10 = persist_top10_and_audit(session, run.id, opportunities, limit=top_limit)

    run.stats = {
        "pipeline_version": "v3",
        "rules": [r.slug for r in rules],
        "fixtures_by_bookmaker": fixtures_by_bookmaker,
        "matches_linked": len(match_by_id),
        "odds_rows_by_rule": dict(odds_count_by_rule),
        "odds_rows_by_bookmaker": dict(odds_count_by_bm),
        "bookmakers": sorted(V3_BOOKMAKER_SLUGS),
        **get_event_fetch_stats(),
        "arbitrage_candidates": len(opportunities),
        "arbitrage_top10": len(top10),
        "min_margin_pct": min_margin,
    }
    run.status = "partial" if errors else "success"
    run.finished_at = datetime.now(tz=timezone.utc)
    run.notes = "; ".join(errors[:30]) if errors else None
    session.commit()

    return {
        "run_id": run.id,
        "status": run.status,
        "stats": run.stats,
        "errors": run.notes,
        "top10": [
            {
                "rank": i + 1,
                "match": f"{o.home_team} vs {o.away_team}",
                "market": o.market_label,
                "line": o.line,
                "margin_pct": o.margin_pct,
                "bookmaker_count": o.bookmaker_count,
                "legs": o.legs,
            }
            for i, o in enumerate(top10)
        ],
    }
