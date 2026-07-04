from __future__ import annotations

import hashlib
import re
import unicodedata

_PERIOD_1H = re.compile(r"\b(1st half|first half|1\s*-?\s*half|първо\s*полувреме)\b", re.I)
_PERIOD_2H = re.compile(r"\b(2nd half|second half|2\s*-?\s*half|второ\s*полувреме)\b", re.I)
_COMBO = re.compile(r"[&+]")
_PROMO = re.compile(r"(0%\s*марж|0%\s*margin|enhanced odds|early payout|ранно изплащане)", re.I)


def normalize_text(value: str) -> str:
    text = value.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text


def detect_period(name: str) -> str:
    n = normalize_text(name)
    if _PERIOD_1H.search(n):
        return "1h"
    if _PERIOD_2H.search(n):
        return "2h"
    return "ft"


def is_combo_market(name: str) -> bool:
    return bool(_COMBO.search(name))


def is_promo_market(name: str) -> bool:
    return bool(_PROMO.search(name))


def parse_odd(value: object) -> float | None:
    if value is None:
        return None
    try:
        odd = float(value)
        return odd if odd > 1.0 else None
    except (TypeError, ValueError):
        return None


def build_canonical_key(
    family: str,
    period: str,
    scope: str,
    line: str | None,
    outcome_roles: tuple[str, ...],
    market_name: str | None = None,
) -> str:
    parts = [family, period, scope or "match"]
    if line:
        parts.append(f"line_{line}")
    if family == "other" and market_name:
        from scraper.v2.market_names import semantic_market_slug

        slug = semantic_market_slug(market_name, line)
        parts.append(f"sem_{slug}")
    parts.append("roles_" + "_".join(sorted(outcome_roles)))
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# Families eligible for cross-bookmaker arbitrage
ARB_ELIGIBLE_FAMILIES = frozenset(
    {
        "match_1x2",
        "total_goals",
        "total_corners",
        "total_cards",
        "total",
        "handicap",
        "btts",
        "double_chance",
        "draw_no_bet",
    }
)

# Semantic slugs that may participate in arb when matched across bookmakers
ARB_ELIGIBLE_SEMANTIC_PREFIXES = (
    "total_goals_",
    "total_corners_",
    "total_cards_",
    "match_result",
    "btts",
    "handicap_",
    "double_chance",
    "draw_no_bet",
)
