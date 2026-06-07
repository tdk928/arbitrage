from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from scraper.markets.extractors import extract_bet365_markets_from_html
from scraper.platforms.base import PlatformScraper
from scraper.types import MarketOdds, RawFixture
from scraper.config import get_settings

HUB_URL = "https://www.bet365.com/hub/en-gb/football/football-competitions/world-cup"


class Bet365Scraper(PlatformScraper):
    slug = "bet365"
    platform = "bet365"

    def list_fixtures(self, discovery_config: dict[str, Any]) -> list[RawFixture]:
        url = discovery_config.get("hub_url", HUB_URL)
        settings = get_settings()
        fixtures: list[RawFixture] = []
        seen: set[str] = set()

        with httpx.Client(
            headers={"User-Agent": settings.user_agent},
            timeout=30,
            follow_redirects=True,
        ) as client:
            html = client.get(url).text

        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(attrs={"data-fixture-id": True, "data-item-name": True}):
            name = (el.get("data-item-name") or "").strip()
            if not re.search(r"\s+v\s+", name, re.I):
                continue
            parts = re.split(r"\s+v\s+", name, maxsplit=1, flags=re.I)
            if len(parts) != 2:
                continue
            home, away = parts[0].strip(), parts[1].strip()
            fixture_id = str(el["data-fixture-id"])
            if fixture_id in seen:
                continue
            kickoff = self._kickoff_from_context(el, html)
            seen.add(fixture_id)
            fixtures.append(
                RawFixture(
                    home_team=home,
                    away_team=away,
                    kickoff_utc=kickoff,
                    external_id=fixture_id,
                    bookmaker_slug=self.slug,
                    raw={"name": name, "fixture_id": fixture_id},
                )
            )

        if not fixtures:
            fixtures = self._parse_pipe_rows(html)
        return fixtures

    def _kickoff_from_context(self, el, html: str) -> datetime:
        text = el.get_text("|", strip=True)
        m = re.search(r"(\d{2})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2}):(\d{2})", text)
        if m:
            day, month, year, hour, minute, _ = m.groups()
            return datetime(
                2000 + int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                tzinfo=timezone.utc,
            )
        name = el.get("data-item-name", "")
        idx = html.find(name)
        if idx >= 0:
            chunk = html[idx : idx + 500]
            m = re.search(r"(\d{2})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2}):(\d{2})", chunk)
            if m:
                day, month, year, hour, minute, _ = m.groups()
                return datetime(
                    2000 + int(year),
                    int(month),
                    int(day),
                    int(hour),
                    int(minute),
                    tzinfo=timezone.utc,
                )
        return datetime.now(tz=timezone.utc)

    def _parse_pipe_rows(self, html: str) -> list[RawFixture]:
        fixtures: list[RawFixture] = []
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("|", strip=True)
        parts = text.split("|")
        i = 0
        while i < len(parts) - 6:
            if re.search(r"\s+v\s+", parts[i], re.I):
                match = re.split(r"\s+v\s+", parts[i], maxsplit=1, flags=re.I)
                if len(match) == 2:
                    home, away = match[0].strip(), match[1].strip()
                    kickoff = datetime.now(tz=timezone.utc)
                    if i + 1 < len(parts):
                        m = re.search(
                            r"(\d{2})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2}):(\d{2})",
                            parts[i + 1],
                        )
                        if m:
                            day, month, year, hour, minute, _ = m.groups()
                            kickoff = datetime(
                                2000 + int(year),
                                int(month),
                                int(day),
                                int(hour),
                                int(minute),
                                tzinfo=timezone.utc,
                            )
                    key = f"{home}|{away}|{kickoff.date().isoformat()}"
                    fixtures.append(
                        RawFixture(
                            home_team=home,
                            away_team=away,
                            kickoff_utc=kickoff,
                            external_id=key,
                            bookmaker_slug=self.slug,
                            raw={"line": parts[i]},
                        )
                    )
            i += 1
        return fixtures

    def fetch_markets(self, external_id: str, discovery_config: dict[str, Any]) -> list[MarketOdds]:
        url = discovery_config.get("hub_url", HUB_URL)
        settings = get_settings()
        with httpx.Client(headers={"User-Agent": settings.user_agent}, timeout=30) as client:
            html = client.get(url).text

        if external_id.isdigit():
            idx = html.find(f'data-fixture-id="{external_id}"')
            if idx >= 0:
                return extract_bet365_markets_from_html(html[idx : idx + 12000])

        if "|" in external_id:
            home = external_id.split("|")[0]
            idx = html.lower().find(home.lower())
            if idx >= 0:
                return extract_bet365_markets_from_html(html[idx : idx + 5000])
        return extract_bet365_markets_from_html(html)
