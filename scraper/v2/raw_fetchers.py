from __future__ import annotations

from typing import Any

import httpx

from scraper.config import get_settings
from scraper.platforms.altenar import ALTENAR_BASE
from scraper.platforms.bet365 import HUB_URL
from scraper.platforms.efbet import EFBET_API, EFBET_HEADERS
from scraper.platforms.egt_digital import EGT_HEADERS
from scraper.v2.bet365_html import extract_all_bet365_markets_from_html
from scraper.v2.raw_extractors import extract_all_markets

_EGT_HOSTS = {
    "winbet": "winbet-api.egt-digital.com",
    "inbet": "inbet-api.egt-digital.com",
}

_ALTENAR_INTEGRATIONS = {
    "palmsbet": "palmsbet.com",
}

# Per-run cache: bet365 hub HTML is large; fetch once per URL
_HUB_HTML_CACHE: dict[str, str] = {}


def clear_fetch_caches() -> None:
    _HUB_HTML_CACHE.clear()


def _fetch_bet365_hub_html(discovery_config: dict[str, Any]) -> str:
    url = discovery_config.get("hub_url", HUB_URL)
    if url in _HUB_HTML_CACHE:
        return _HUB_HTML_CACHE[url]
    settings = get_settings()
    with httpx.Client(
        headers={"User-Agent": settings.user_agent},
        timeout=30,
        follow_redirects=True,
    ) as client:
        html = client.get(url).text
    _HUB_HTML_CACHE[url] = html
    return html


def fetch_raw_payload(
    bookmaker_slug: str,
    platform: str,
    external_id: str,
    discovery_config: dict[str, Any],
) -> dict[str, Any] | None:
    if platform == "egt":
        host = _EGT_HOSTS.get(bookmaker_slug)
        if not host:
            return None
        url = (
            f"https://{host}/api/sportsapi/public/sport-events/"
            f"eventview/normalized/{external_id}"
        )
        with httpx.Client(headers=EGT_HEADERS, timeout=30) as client:
            return client.get(url).json()

    if platform == "altenar":
        integration = _ALTENAR_INTEGRATIONS.get(bookmaker_slug) or discovery_config.get(
            "integration"
        )
        if not integration:
            return None
        params = {
            "culture": "bg-BG",
            "integration": integration,
            "eventId": external_id,
            "timezoneOffset": -180,
            "countryCode": "BG",
            "deviceType": 1,
            "numFormat": "en-GB",
        }
        with httpx.Client(timeout=30) as client:
            return client.get(f"{ALTENAR_BASE}/GetEventDetails", params=params).json()

    if platform == "efbet":
        tab_id = discovery_config.get("tab_id", 59354)
        with httpx.Client(headers=EFBET_HEADERS, timeout=30) as client:
            details = client.get(
                f"{EFBET_API}/sport-event/details",
                params={"sportEventId": external_id, "lang": "bg"},
            ).json()
            listing = client.get(
                f"{EFBET_API}/home-page/prematch-section/{tab_id}/limited",
                params={"lang": "bg"},
            ).json()
            for section in listing:
                for tab in section.get("tabs", []):
                    for ev in tab.get("sportEvents", []):
                        if str(ev.get("id")) == str(external_id):
                            return {"details": details, "listing_event": ev}
            return {"details": details}

    if platform == "bet365":
        html = _fetch_bet365_hub_html(discovery_config)
        return {"html": html, "external_id": external_id}

    if platform == "sportinno":
        from scraper.platforms.registry import get_scraper

        scraper = get_scraper(bookmaker_slug)
        bid = discovery_config.get("bid", "1294778290")
        url = f"https://cdn-bg-api.sportinno.net/api/v2/widgets/events/{external_id}"
        data = None
        for attempt in range(2):
            data = scraper._get_json(url, {"bid": bid})
            if data and len(data.get("marketTypes") or []) > 10:
                scraper._event_cache[str(external_id)] = data
                return data
            scraper._token = None
        cached = scraper._event_cache.get(str(external_id))
        if cached and cached.get("marketTypes"):
            return cached
        if not data:
            return None
        return data if "marketTypes" in data else data.get("sportEvent", data)

    return None


def fetch_all_markets_for_event(
    bookmaker_slug: str,
    platform: str,
    external_id: str,
    discovery_config: dict[str, Any],
) -> list:
    payload = fetch_raw_payload(bookmaker_slug, platform, external_id, discovery_config)
    if not payload:
        return []

    if platform == "efbet":
        from scraper.v2.raw_extractors import extract_all_efbet_markets

        markets = extract_all_efbet_markets(payload.get("details") or {}, bookmaker_slug)
        listing = payload.get("listing_event")
        if listing:
            seen = {m.external_id for m in markets}
            for m in extract_all_efbet_markets(listing, bookmaker_slug):
                if m.external_id not in seen:
                    markets.append(m)
        return markets

    if platform == "bet365":
        return extract_all_bet365_markets_from_html(
            payload["html"],
            external_id=str(payload.get("external_id") or external_id),
            bookmaker_slug=bookmaker_slug,
        )

    return extract_all_markets(platform, payload, bookmaker_slug)
