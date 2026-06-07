from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from scraper.markets.extractors import extract_efbet_markets
from scraper.platforms.base import PlatformScraper
from scraper.types import MarketOdds, RawFixture
from scraper.normalize import split_fixture_name

EFBET_API = "https://apigw.efbet.com/api/v1/sport-event/public"
EFBET_HEADERS = {
    "Accept": "application/json",
    "Origin": "https://efbet.com",
    "Referer": "https://efbet.com/bg/sport",
}


class EfbetScraper(PlatformScraper):
    slug = "efbet"
    platform = "efbet"

    def list_fixtures(self, discovery_config: dict[str, Any]) -> list[RawFixture]:
        tab_id = discovery_config.get("tab_id", 59354)
        fixtures: list[RawFixture] = []
        url = f"{EFBET_API}/home-page/prematch-section/{tab_id}/limited"
        with httpx.Client(headers=EFBET_HEADERS, timeout=30) as client:
            data = client.get(url, params={"lang": "bg"}).json()
        for section in data:
            for tab in section.get("tabs", []):
                for ev in tab.get("sportEvents", []):
                    name = ev.get("englishName") or ev.get("name") or ""
                    teams = split_fixture_name(name.replace(" - ", " vs "))
                    if not teams:
                        continue
                    start = ev.get("startTime")
                    if not start:
                        continue
                    kickoff = datetime.fromisoformat(start.replace("Z", "+00:00"))
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
        by_code: dict[str, MarketOdds] = {}
        tab_id = discovery_config.get("tab_id", 59354)
        with httpx.Client(headers=EFBET_HEADERS, timeout=30) as client:
            listing_url = f"{EFBET_API}/home-page/prematch-section/{tab_id}/limited"
            data = client.get(listing_url, params={"lang": "bg"}).json()
            for section in data:
                for tab in section.get("tabs", []):
                    for ev in tab.get("sportEvents", []):
                        if str(ev.get("id")) == str(external_id):
                            for m in extract_efbet_markets(ev):
                                by_code[m.market_code] = m
            details = client.get(
                f"{EFBET_API}/sport-event/details",
                params={"sportEventId": external_id, "lang": "bg"},
            ).json()
            for m in extract_efbet_markets(details):
                by_code[m.market_code] = m
        return list(by_code.values())
