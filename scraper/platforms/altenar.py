from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from scraper.markets.extractors import extract_altenar_markets
from scraper.platforms.base import PlatformScraper
from scraper.types import MarketOdds, RawFixture
from scraper.normalize import split_fixture_name

ALTENAR_BASE = "https://sb2frontend-altenar2.biahosted.com/api/widget"


class AltenarScraper(PlatformScraper):
    def __init__(self, slug: str, integration: str):
        self.slug = slug
        self.platform = "altenar"
        self.integration = integration

    def list_fixtures(self, discovery_config: dict[str, Any]) -> list[RawFixture]:
        champ_id = discovery_config.get("champ_id")
        sport_id = discovery_config.get("sport_id", 66)
        endpoint = discovery_config.get("endpoint") or ("GetEvents" if champ_id else "GetUpcoming")
        fixtures: list[RawFixture] = []
        params = {
            "culture": "bg-BG",
            "integration": self.integration,
            "sportId": sport_id,
            "timezoneOffset": -180,
            "countryCode": "BG",
            "deviceType": 1,
            "numFormat": "en-GB",
        }
        if champ_id:
            params["champIds"] = champ_id
        url = f"{ALTENAR_BASE}/{endpoint}"
        with httpx.Client(timeout=30) as client:
            data = client.get(url, params=params).json()
        events = data if isinstance(data, list) else data.get("events", [])
        for ev in events:
            if champ_id and ev.get("champId") not in (None, champ_id):
                continue
            name = ev.get("name") or ""
            teams = split_fixture_name(name)
            if not teams:
                continue
            start = ev.get("startDate") or ev.get("et")
            if not start:
                continue
            kickoff = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            fixtures.append(
                RawFixture(
                    home_team=teams[0],
                    away_team=teams[1],
                    kickoff_utc=kickoff,
                    external_id=str(ev.get("id")),
                    bookmaker_slug=self.slug,
                    raw=ev,
                )
            )
        return fixtures

    def fetch_markets(self, external_id: str, discovery_config: dict[str, Any]) -> list[MarketOdds]:
        params = {
            "culture": "bg-BG",
            "integration": self.integration,
            "eventId": external_id,
            "timezoneOffset": -180,
            "countryCode": "BG",
            "deviceType": 1,
            "numFormat": "en-GB",
        }
        url = f"{ALTENAR_BASE}/GetEventDetails"
        with httpx.Client(timeout=30) as client:
            data = client.get(url, params=params).json()
        return extract_altenar_markets(data)
