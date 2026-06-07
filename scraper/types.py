from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawFixture:
    home_team: str
    away_team: str
    kickoff_utc: datetime
    external_id: str
    bookmaker_slug: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutcomeOdd:
    name: str
    odd: float


@dataclass
class MarketOdds:
    market_code: str
    outcomes: list[OutcomeOdd]
    line: str | None = None
