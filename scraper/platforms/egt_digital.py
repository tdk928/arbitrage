from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import httpx

from scraper.markets.extractors import extract_egt_markets
from scraper.platforms.base import PlatformScraper
from scraper.types import MarketOdds, RawFixture
from scraper.normalize import split_fixture_name

EGT_HEADERS = {
    "X-Platform-Lang": "bg",
    "X-Platform-TZ": "180",
    "X-Platform-Device": "desktop",
    "Accept": "application/json",
}

YOUTH_PATTERN = re.compile(r"\b(u19|u20|u21|u23|u17|ii|2)\b", re.I)


class EgtScraper(PlatformScraper):
    def __init__(self, slug: str, api_host: str):
        self.slug = slug
        self.platform = "egt"
        self.api_host = api_host

    def list_fixtures(self, discovery_config: dict[str, Any]) -> list[RawFixture]:
        tournament_name = discovery_config.get("tournament_name", "Световно Първенство")
        search_terms = discovery_config.get(
            "search_terms",
            ["South Africa", "Mexico", "Germany", "Brazil", "England"],
        )
        fixtures: list[RawFixture] = []
        seen: set[str] = set()

        with httpx.Client(headers=EGT_HEADERS, timeout=30) as client:
            for term in search_terms:
                q = httpx.QueryParams({"searchTerm": term, "verticalType": "sports"})
                url = (
                    f"https://{self.api_host}/api/sportsapi/public/search/events-data?{q}"
                )
                try:
                    data = client.get(url).json()
                    for group in data if isinstance(data, list) else []:
                        for ev in group.get("events", []):
                            tour = ev.get("tournamentName") or ""
                            if tournament_name.lower() not in tour.lower():
                                continue
                            if not self._is_eligible_fixture(ev):
                                continue
                            fx = self._to_fixture(ev)
                            if fx and fx.external_id not in seen:
                                seen.add(fx.external_id)
                                fixtures.append(fx)
                except Exception:
                    continue
        return fixtures

    def _is_eligible_fixture(self, ev: dict) -> bool:
        home = ev.get("homeTeam") or ""
        away = ev.get("awayTeam") or ""
        label = f"{home} {away}"
        if YOUTH_PATTERN.search(label):
            return False
        if home and away and home.strip().lower() == away.strip().lower():
            return False
        return True

    def _to_fixture(self, ev: dict) -> RawFixture | None:
        home = ev.get("homeTeam")
        away = ev.get("awayTeam")
        if home and away:
            teams = (home, away)
        else:
            name = ev.get("name") or ev.get("eventName") or ""
            teams = split_fixture_name(name.replace(".", " vs "))
        if not teams:
            return None
        start = ev.get("scheduledTime") or ev.get("startTime") or ev.get("startDate")
        if not start:
            return None
        kickoff = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        eid = str(ev.get("id") or ev.get("eventId") or "")
        if not eid:
            return None
        return RawFixture(
            home_team=teams[0],
            away_team=teams[1],
            kickoff_utc=kickoff,
            external_id=eid,
            bookmaker_slug=self.slug,
            raw=ev,
        )

    def fetch_markets(self, external_id: str, discovery_config: dict[str, Any]) -> list[MarketOdds]:
        url = (
            f"https://{self.api_host}/api/sportsapi/public/sport-events/"
            f"eventview/normalized/{external_id}"
        )
        with httpx.Client(headers=EGT_HEADERS, timeout=30) as client:
            data = client.get(url).json()
        return extract_egt_markets(data)
