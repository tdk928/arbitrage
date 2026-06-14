from __future__ import annotations

from typing import Any

import httpx

from scraper.platforms.altenar import ALTENAR_BASE
from scraper.platforms.efbet import EFBET_API, EFBET_HEADERS
from scraper.platforms.egt_digital import EGT_HEADERS
from scraper.v2.raw_extractors import extract_all_markets

_EGT_HOSTS = {
    "winbet": "winbet-api.egt-digital.com",
    "inbet": "inbet-api.egt-digital.com",
}

_ALTENAR_INTEGRATIONS = {
    "palmsbet": "palmsbet.com",
}


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
            from scraper.v2.raw_extractors import extract_all_efbet_markets as extract_efbet

            seen = {m.external_id for m in markets}
            for m in extract_efbet(listing, bookmaker_slug):
                if m.external_id not in seen:
                    markets.append(m)
        return markets

    return extract_all_markets(platform, payload, bookmaker_slug)
