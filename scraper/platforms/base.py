from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from scraper.types import MarketOdds, RawFixture


class PlatformScraper(ABC):
    slug: str
    platform: str

    @abstractmethod
    def list_fixtures(self, discovery_config: dict[str, Any]) -> list[RawFixture]:
        raise NotImplementedError

    @abstractmethod
    def fetch_markets(self, external_id: str, discovery_config: dict[str, Any]) -> list[MarketOdds]:
        raise NotImplementedError
