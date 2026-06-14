from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedOutcome:
    role: str
    name: str
    odd: float


@dataclass
class ParsedMarket:
    external_id: str
    market_name: str
    platform: str
    bookmaker_slug: str
    family: str
    period: str
    scope: str
    line: str | None
    outcomes: list[ParsedOutcome]
    provider_template: str | None = None
    specifiers: dict[str, Any] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    mapped: bool = True

    @property
    def outcome_roles(self) -> tuple[str, ...]:
        return tuple(o.role for o in self.outcomes)

    @property
    def label(self) -> str:
        period_label = {"ft": "FT", "1h": "1H", "2h": "2H"}.get(self.period, self.period.upper())
        base = self.family.replace("_", " ").title()
        parts = [base, period_label]
        if self.line:
            parts.append(f"line {self.line}")
        if self.scope != "match":
            parts.append(self.scope)
        return " · ".join(parts)


# Bookmakers supported in v2 (EGT + Altenar + efbet + bet365 hub)
V2_BOOKMAKER_SLUGS = frozenset({"efbet", "winbet", "inbet", "palmsbet", "bet365"})

V2_PLATFORMS = frozenset({"egt", "altenar", "efbet", "bet365"})
