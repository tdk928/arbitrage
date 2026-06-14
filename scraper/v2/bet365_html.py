from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from scraper.v2.canonical import detect_period, parse_odd
from scraper.v2.types import ParsedMarket, ParsedOutcome

_CATEGORY_TO_FAMILY = {
    "full time result": "match_1x2",
    "match result": "match_1x2",
    "1x2": "match_1x2",
    "goal line": "total_goals",
    "match goals": "total_goals",
    "total goals": "total_goals",
    "asian handicap": "handicap",
    "handicap result": "handicap",
    "both teams to score": "btts",
    "corners": "total_corners",
    "corner line": "total_corners",
}

_LINE_IN_NAME = re.compile(r"(\d+\.?\d*)")


def _fractional_to_decimal(value: str) -> float | None:
    value = value.strip()
    if "/" not in value:
        return parse_odd(value)
    num, den = value.split("/", 1)
    try:
        return round(1 + int(num) / int(den), 4)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _parse_decimal_attr(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return parse_odd(float(value))
    except (TypeError, ValueError):
        return None


def _outcome_role_from_button(label: str, variant: str, category: str) -> str:
    label = label.strip().upper()
    if label in ("1", "X", "2"):
        return label
    variant_l = variant.lower()
    if "home" in variant_l:
        return "1"
    if "draw" in variant_l:
        return "X"
    if "away" in variant_l:
        return "2"
    if label.lower() in ("over", "under", "yes", "no"):
        return label.lower()
    return label.lower().replace(" ", "_")[:32]


def _family_from_category(category: str, market_name: str) -> tuple[str, str | None]:
    cat = category.strip().lower()
    family = _CATEGORY_TO_FAMILY.get(cat, "other")
    line = None
    if family in ("total_goals", "total_corners", "handicap", "total"):
        m = _LINE_IN_NAME.search(market_name)
        if m:
            line = m.group(1)
    return family, line


def extract_all_bet365_markets_from_html(
    html: str,
    external_id: str | None = None,
    bookmaker_slug: str = "bet365",
) -> list[ParsedMarket]:
    """
    Parse bet365 hub HTML. The public hub exposes fixture odds via fxt-Odd buttons;
    currently Full Time Result (1X2) per fixture. Additional categories are parsed
    when present in the HTML structure.
    """
    soup = BeautifulSoup(html, "html.parser")

    if external_id and not str(external_id).isdigit():
        if "|" in str(external_id):
            home = str(external_id).split("|")[0].strip().lower()
            for el in soup.find_all(attrs={"data-item-name": True}):
                name = (el.get("data-item-name") or "").lower()
                if name.startswith(home):
                    external_id = el.get("data-item-id") or el.get("data-fixture-id")
                    break

    by_fixture: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for btn in soup.find_all("button", class_="fxt-Odd"):
        fid = btn.get("data-item-id")
        if not fid:
            continue
        if external_id and str(fid) != str(external_id):
            continue

        category = btn.get("data-item-category3") or "Unknown"
        variant = btn.get("data-item-variant") or ""
        decimal_raw = btn.get("data-item-odds")
        span = btn.find("span")
        label = span.get_text(strip=True) if span else ""
        text = btn.get_text(strip=True)
        fractional = text.replace(label, "").strip() if label else text

        odd = _parse_decimal_attr(decimal_raw) or _fractional_to_decimal(fractional)
        if not odd:
            continue

        by_fixture.setdefault(str(fid), {}).setdefault(category, []).append(
            {
                "label": label,
                "variant": variant,
                "odd": odd,
                "category": category,
            }
        )

    markets: list[ParsedMarket] = []
    for fid, categories in by_fixture.items():
        for category, items in categories.items():
            if len(items) < 2 and category.lower() not in ("full time result",):
                continue

            market_name = category
            family, line = _family_from_category(category, market_name)
            period = detect_period(category)
            outcomes: list[ParsedOutcome] = []

            for item in items:
                role = _outcome_role_from_button(
                    item["label"], item["variant"], category
                )
                display = item["label"] or item["variant"] or role
                outcomes.append(
                    ParsedOutcome(role=role, name=display, odd=item["odd"])
                )

            if family == "match_1x2":
                roles = {o.role for o in outcomes}
                if roles != {"1", "X", "2"} or len(outcomes) != 3:
                    continue
                outcomes = sorted(outcomes, key=lambda o: ("1", "X", "2").index(o.role))

            if len(outcomes) < 2:
                continue

            markets.append(
                ParsedMarket(
                    external_id=f"{fid}:{category}",
                    market_name=market_name,
                    platform="bet365",
                    bookmaker_slug=bookmaker_slug,
                    family=family,
                    period=period,
                    scope="match",
                    line=line,
                    outcomes=outcomes,
                    provider_template=category,
                    raw_payload={"fixture_id": fid, "category": category, "items": items},
                )
            )

    return markets
