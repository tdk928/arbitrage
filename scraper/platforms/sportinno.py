from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from curl_cffi import requests as curl_requests

from scraper.markets.extractors import extract_sportinno_markets
from scraper.platforms.altenar import AltenarScraper
from scraper.platforms.base import PlatformScraper
from scraper.types import MarketOdds, RawFixture

SPORTINNO_API_V2 = "https://cdn-bg-api.sportinno.net/api/v2"
SPORTINNO_API_V3 = "https://cdn-bg-api.sportinno.net/api/v3"
APP_ID = "b53bcf18-f25d-4e38-92ee-44557fb14fb6"
DEFAULT_BID = "1294778290"
IMPERSONATE = "chrome120"


class SportInnoScraper(PlatformScraper):
    slug = "8888"
    platform = "sportinno"

    def __init__(self):
        self._token: str | None = None
        self._event_cache: dict[str, dict] = {}
        self._altenar_event_ids: set[str] = set()
        self._altenar_config: dict[str, Any] = {}

    def _base_headers(self) -> dict[str, str]:
        return {
            "Origin": "https://8888.bg",
            "Referer": "https://8888.bg/sport/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _login(self) -> str:
        if self._token:
            return self._token
        resp = curl_requests.post(
            f"{SPORTINNO_API_V2}/user/dedicated/login",
            json={"appId": APP_ID, "language": "bg", "isDemo": False},
            headers={
                **self._base_headers(),
                "Content-Type": "application/json",
                "tenantId": "1",
            },
            impersonate=IMPERSONATE,
            timeout=30,
        )
        resp.raise_for_status()
        self._token = resp.json()["authorizationToken"]
        return self._token

    def _auth_headers(self) -> dict[str, str]:
        return {
            **self._base_headers(),
            "Authorization": f"Bearer {self._login()}",
            "tenantId": "1",
        }

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> dict | None:
        resp = curl_requests.get(
            url,
            params=params or {},
            headers=self._auth_headers(),
            impersonate=IMPERSONATE,
            timeout=30,
        )
        if resp.status_code != 200 or not resp.text:
            return None
        try:
            return resp.json()
        except Exception:
            return None

    def list_fixtures(self, discovery_config: dict[str, Any]) -> list[RawFixture]:
        tournament_id = discovery_config.get("tournament_id", 56878)
        bid = discovery_config.get("bid", DEFAULT_BID)
        self._altenar_event_ids.clear()
        self._altenar_config = discovery_config.get("altenar_fallback") or {}
        fixtures: list[RawFixture] = []
        seen: set[str] = set()

        tournament_data = self._get_json(
            f"{SPORTINNO_API_V3}/widgets/tournaments/{tournament_id}",
            {"bid": bid},
        )
        if tournament_data:
            fixtures.extend(self._parse_sports_tree(tournament_data, tournament_id))

        if not fixtures:
            derby_data = self._get_json(
                f"{SPORTINNO_API_V3}/widgets/derby-events",
                {"bid": bid},
            )
            if derby_data:
                fixtures.extend(self._parse_sports_tree(derby_data, tournament_id))

        for fx in fixtures:
            seen.add(fx.external_id)

        if not fixtures and self._altenar_config:
            alt = AltenarScraper(self.slug, self._altenar_config.get("integration", "8888.bg"))
            for fx in alt.list_fixtures(self._altenar_config):
                if fx.external_id in seen:
                    continue
                seen.add(fx.external_id)
                self._altenar_event_ids.add(fx.external_id)
                fx.raw = {**(fx.raw or {}), "source": "altenar_fallback"}
                fixtures.append(fx)

        return fixtures

    def _parse_sports_tree(self, data: dict, tournament_id: int) -> list[RawFixture]:
        fixtures: list[RawFixture] = []
        for sport in data.get("sports", []):
            for cat in sport.get("categories", []):
                for tour in cat.get("tournaments", []):
                    if tournament_id and tour.get("id") != tournament_id:
                        continue
                    for ev in tour.get("sportEvents", []):
                        fx = self._event_to_fixture(ev)
                        if fx:
                            fixtures.append(fx)
        if "sportSections" in data:
            for section in data.get("sportSections", []):
                for ev in section.get("events", []):
                    fx = self._event_to_fixture(ev)
                    if fx:
                        fixtures.append(fx)
        return fixtures

    def _event_to_fixture(self, ev: dict) -> RawFixture | None:
        teams = ev.get("teams") or []
        if len(teams) >= 2:
            home, away = teams[0].get("name", "").strip(), teams[1].get("name", "").strip()
        else:
            name = ev.get("name", "")
            for sep in (" vs ", " vs. "):
                if sep in name:
                    parts = name.split(sep, 1)
                    home, away = parts[0].strip(), parts[1].strip()
                    break
            else:
                return None
        if not home or not away or home.lower() == away.lower():
            return None
        start = ev.get("startTime")
        if not start:
            return None
        kickoff = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        eid = str(ev.get("id") or ev.get("externalId") or "")
        if not eid:
            return None
        self._event_cache[eid] = ev
        return RawFixture(
            home_team=home,
            away_team=away,
            kickoff_utc=kickoff,
            external_id=eid,
            bookmaker_slug=self.slug,
            raw=ev,
        )

    def fetch_markets(self, external_id: str, discovery_config: dict[str, Any]) -> list[MarketOdds]:
        bid = discovery_config.get("bid", DEFAULT_BID)
        cached = self._event_cache.get(str(external_id))
        if cached and cached.get("marketTypes"):
            return extract_sportinno_markets(cached)

        if str(external_id) in self._altenar_event_ids:
            alt_cfg = discovery_config.get("altenar_fallback") or self._altenar_config
            if alt_cfg:
                alt = AltenarScraper(self.slug, alt_cfg.get("integration", "8888.bg"))
                return alt.fetch_markets(external_id, alt_cfg)

        data = self._get_json(
            f"{SPORTINNO_API_V2}/widgets/events/{external_id}",
            {"bid": bid},
        )
        if not data or data.get("success") is False:
            return []
        event = data if "marketTypes" in data else data.get("sportEvent", data)
        return extract_sportinno_markets(event)
