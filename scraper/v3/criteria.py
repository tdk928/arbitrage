from __future__ import annotations

from typing import Any

from scraper.v2.types import ParsedMarket
from scraper.v3.line_filter import is_half_line


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(n.lower() in lowered for n in needles)


def _excludes_all(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return not any(n.lower() in lowered for n in needles)


def _type_id_matches(market: ParsedMarket, type_id: int) -> bool:
    template = (market.provider_template or "").lower()
    if template == f"typeid:{type_id}":
        return True
    if market.specifiers.get("type_id") == type_id:
        return True
    return False


def criteria_match(criteria: dict[str, Any], market: ParsedMarket) -> bool:
    if criteria.get("line_filter") == "half_only" and not is_half_line(market.line):
        return False

    required = criteria.get("required_outcome_roles") or ["over", "under"]
    roles = {o.role for o in market.outcomes}
    if not set(required).issubset(roles):
        return False

    if exact := criteria.get("market_name"):
        name_l = market.market_name.strip().lower()
        exact_l = str(exact).strip().lower()
        if criteria.get("market_name_exact"):
            if name_l != exact_l:
                return False
        elif name_l != exact_l and not name_l.startswith(exact_l + " "):
            return False

    if contains := criteria.get("market_name_contains"):
        if str(contains).lower() not in market.market_name.lower():
            return False

    if any_list := criteria.get("market_name_contains_any"):
        if not _contains_any(market.market_name, any_list):
            return False

    if excl := criteria.get("market_name_excludes_any"):
        if not _excludes_all(market.market_name, excl):
            return False

    if template := criteria.get("radar_template"):
        if (market.provider_template or "").lower() != str(template).lower():
            return False

    if templates := criteria.get("radar_template_any"):
        pt = (market.provider_template or "").lower()
        if pt not in {str(t).lower() for t in templates}:
            return False

    if type_id := criteria.get("type_id"):
        if not _type_id_matches(market, int(type_id)):
            return False

    if group := criteria.get("market_group_name"):
        group_l = str(group).strip().lower()
        spec_group = str(market.specifiers.get("group_name") or "").strip().lower()
        if spec_group:
            if spec_group != group_l:
                return False
        elif group_l not in market.market_name.lower():
            return False

    if orig_contains := criteria.get("original_name_contains"):
        orig = str(market.specifiers.get("original_name") or "").lower()
        if str(orig_contains).lower() not in orig:
            return False

    if orig_excl := criteria.get("original_name_excludes_any"):
        orig = str(market.specifiers.get("original_name") or "").lower()
        if any(x.lower() in orig for x in orig_excl):
            return False

    if criteria.get("original_name_ends_with_line"):
        if not market.line:
            return False
        orig = str(market.specifiers.get("original_name") or "").strip()
        line = str(market.line).strip()
        if not orig.lower().endswith(line.lower()):
            return False

    return True
