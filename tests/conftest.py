from __future__ import annotations

import pytest

from scraper.v2.types import ParsedMarket, ParsedOutcome


@pytest.fixture
def make_market():
    def _factory(**kwargs) -> ParsedMarket:
        defaults: dict = {
            "external_id": "m1",
            "market_name": "Test market",
            "platform": "betano",
            "bookmaker_slug": "betano",
            "family": "total_goals",
            "period": "ft",
            "scope": "match",
            "line": "2.5",
            "outcomes": [
                ParsedOutcome(role="over", name="Над", odd=1.9),
                ParsedOutcome(role="under", name="Под", odd=1.9),
            ],
            "provider_template": None,
            "specifiers": {},
        }
        defaults.update(kwargs)
        return ParsedMarket(**defaults)

    return _factory
