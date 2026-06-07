from __future__ import annotations

import httpx

from scraper.config import get_settings


def build_client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        timeout=settings.http_timeout,
        headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
        follow_redirects=True,
    )


def get_json(client: httpx.Client, url: str, **kwargs) -> dict | list:
    resp = client.get(url, **kwargs)
    resp.raise_for_status()
    return resp.json()
