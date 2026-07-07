from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from curl_cffi import requests

from scraper.platforms.base import PlatformScraper
from scraper.types import MarketOdds, OutcomeOdd, RawFixture
from scraper.v2.raw_extractors import extract_all_betano_markets
from scraper.v2.types import ParsedMarket

BETANO_BASE = "https://www.betano.bg"
BETANO_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "bg-BG,bg;q=0.9",
    "Referer": f"{BETANO_BASE}/",
}
DEFAULT_EVENTS_REQ = "la,s,stnf,c,mb,mbl"


def _session() -> requests.Session:
    return requests.Session(impersonate="chrome120", headers=BETANO_HEADERS)


def _tournament_events_url(discovery_config: dict[str, Any]) -> str:
    sport = discovery_config.get("sport_slug", "futbol")
    tournament = discovery_config.get("tournament_slug", "svetovno-pervenstvo")
    tournament_id = discovery_config.get("tournament_id")
    req = discovery_config.get("events_req", DEFAULT_EVENTS_REQ)
    return f"{BETANO_BASE}/api/sport/{sport}/turniri/{tournament}/{tournament_id}/events/?req={req}"


def _event_api_url(event_url: str, discovery_config: dict[str, Any]) -> str:
    req = discovery_config.get("events_req", DEFAULT_EVENTS_REQ)
    path = event_url if event_url.startswith("/") else f"/{event_url}"
    if not path.endswith("/"):
        path += "/"
    return f"{BETANO_BASE}/api{path}?req={req}"


def _iter_tournament_events(data: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            event_id = node.get("id")
            participants = node.get("participants")
            if event_id and participants and str(event_id) not in seen:
                seen.add(str(event_id))
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data.get("data", data))
    return found


def _kickoff_from_ms(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class BetanoScraper(PlatformScraper):
    slug = "betano"
    platform = "betano"

    def list_fixtures(self, discovery_config: dict[str, Any]) -> list[RawFixture]:
        url = _tournament_events_url(discovery_config)
        data = _session().get(url, timeout=30).json()
        fixtures: list[RawFixture] = []
        for ev in _iter_tournament_events(data):
            participants = ev.get("participants") or []
            if len(participants) < 2:
                continue
            home = str(participants[0].get("name", "")).strip()
            away = str(participants[1].get("name", "")).strip()
            if not home or not away:
                continue
            kickoff = _kickoff_from_ms(ev.get("startTime"))
            if not kickoff:
                continue
            event_url = str(ev.get("url") or "").strip()
            fixtures.append(
                RawFixture(
                    home_team=home,
                    away_team=away,
                    kickoff_utc=kickoff,
                    external_id=str(ev.get("id")),
                    bookmaker_slug=self.slug,
                    raw={"event_url": event_url, **ev},
                )
            )
        return fixtures

    def fetch_event_payload(
        self, external_id: str, discovery_config: dict[str, Any], event_url: str | None = None
    ) -> dict[str, Any] | None:
        if not event_url:
            fixtures = self.list_fixtures(discovery_config)
            for fx in fixtures:
                if str(fx.external_id) == str(external_id):
                    event_url = (fx.raw or {}).get("event_url")
                    break
        if not event_url:
            return None
        url = _event_api_url(str(event_url), discovery_config)
        data = _session().get(url, timeout=30).json()
        event = (data.get("data") or {}).get("event")
        if not event or str(event.get("id")) != str(external_id):
            return None
        return data

    def fetch_markets(self, external_id: str, discovery_config: dict[str, Any]) -> list[MarketOdds]:
        parsed = self.fetch_parsed_markets(external_id, discovery_config)
        return [
            MarketOdds(
                market_code=p.external_id,
                line=p.line,
                outcomes=[OutcomeOdd(name=o.name, odd=o.odd) for o in p.outcomes],
            )
            for p in parsed
        ]

    def fetch_parsed_markets(
        self, external_id: str, discovery_config: dict[str, Any]
    ) -> list[ParsedMarket]:
        payload = self.fetch_event_payload(external_id, discovery_config)
        if not payload:
            return []
        return extract_all_betano_markets(payload, self.slug)
