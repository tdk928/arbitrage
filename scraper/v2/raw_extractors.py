from __future__ import annotations

import re
from typing import Any

from scraper.markets.extractors import _iter_efbet_markets
from scraper.v2.canonical import (
    detect_period,
    is_combo_market,
    is_promo_market,
    normalize_text,
    parse_odd,
)
from scraper.v2.types import ParsedMarket, ParsedOutcome

_EGT_CORNERS = re.compile(r"^total corners (8\.5|9\.5)$", re.I)
_EGT_GOALS_25 = re.compile(r"^total goals 2\.5$", re.I)
_EGT_LINE_IN_NAME = re.compile(
    r"(?:total goals|total corners)\s+(\d+(?:\.\d+)?)", re.I
)
_ALT_GOALS = re.compile(r"^общ брой(?: голове)?$", re.I)
_ALT_CORNERS = re.compile(r"^общ брой корнери$", re.I)
_ALT_DRAW = frozenset({"равенство", "x", "draw", "равен"})
_OU_OVER = frozenset({"over", "над"})
_OU_UNDER = frozenset({"under", "под"})


def _outcomes_from_egt(outcomes_raw: list[dict]) -> list[ParsedOutcome]:
    outs: list[ParsedOutcome] = []
    for o in outcomes_raw:
        name = str(o.get("name", "")).strip()
        odd = parse_odd(o.get("odds"))
        if not odd:
            continue
        label = name.lower()
        if label in ("1", "x", "2"):
            role = "X" if label == "x" else label.upper()
        elif label in _OU_OVER:
            role = "over"
        elif label in _OU_UNDER:
            role = "under"
        elif label in ("yes", "да"):
            role = "yes"
        elif label in ("no", "не"):
            role = "no"
        else:
            role = normalize_text(name).replace(" ", "_")[:32] or "unknown"
        outs.append(ParsedOutcome(role=role, name=name, odd=odd))
    return outs


def _egt_family(template: str | None, name: str, market: dict) -> tuple[str, str | None, str]:
    """Return (family, line, scope)."""
    n = name.strip()
    nl = n.lower()
    period = detect_period(n)
    line = str(market.get("specialOddsValue") or market.get("line") or "").strip() or None
    if not line:
        line_match = _EGT_LINE_IN_NAME.search(n)
        if line_match:
            line = line_match.group(1)

    if template == "3Way":
        if "full time result" in nl or "краен" in nl:
            return "match_1x2", None, "match"
        return "match_1x2_other", None, "match"

    if re.match(r"^total corners \d+\.?\d*$", nl):
        line_match = _EGT_LINE_IN_NAME.search(n) or re.search(r"(\d+\.?\d*)", n)
        corner_line = line_match.group(1) if line_match else line
        return "total_corners", corner_line, "match"

    if template == "total":
        if _EGT_GOALS_25.match(nl) or (line == "2.5" and "goal" in nl):
            return "total_goals", "2.5", "match"
        if _EGT_CORNERS.match(nl):
            m = _EGT_CORNERS.match(nl)
            return "total_corners", m.group(1) if m else line, "match"
        if line:
            if "corner" in nl or "корнер" in nl:
                return "total_corners", line, "match"
            if "goal" in nl or "голов" in nl:
                return "total_goals", line, "match"
        return "total", line, "match"

    if template == "handicap":
        return "handicap", line, "match"

    if template in ("BothTeamsToScore", "BothTeamsToScoreMarket"):
        return "btts", None, "match"

    return "other", line, "match"


def _is_egt_full_time_1x2(name: str, template: str | None) -> bool:
    return template == "3Way" and "full time result" in name.lower()


def extract_all_egt_markets(data: dict[str, Any], bookmaker_slug: str) -> list[ParsedMarket]:
    markets: list[ParsedMarket] = []
    markets_data = data.get("marketsData") or {}

    for mid, m in markets_data.items():
        raw_name = str(m.get("name") or "")
        template = m.get("radarMarketTemplateName")
        if not raw_name or is_combo_market(raw_name):
            continue
        if is_promo_market(raw_name) and not _is_egt_full_time_1x2(raw_name, template):
            continue

        outcomes_raw = m.get("outcomes") or []
        outs = _outcomes_from_egt(outcomes_raw)
        if len(outs) < 2:
            continue

        family, line, scope = _egt_family(template, raw_name, m)
        period = detect_period(raw_name)

        # Normalize 1X2 roles
        if family == "match_1x2" and len(outs) == 3:
            roles = {o.role for o in outs}
            if roles == {"1", "X", "2"}:
                outs = sorted(outs, key=lambda o: ("1", "X", "2").index(o.role))

        markets.append(
            ParsedMarket(
                external_id=str(mid),
                market_name=raw_name,
                platform="egt",
                bookmaker_slug=bookmaker_slug,
                family=family,
                period=period,
                scope=scope,
                line=line,
                outcomes=outs,
                provider_template=str(template) if template else None,
                specifiers={"specialOddsValue": m.get("specialOddsValue")},
                raw_payload=m,
            )
        )
    return markets


def _altenar_outcome_role(name: str) -> str:
    n = name.strip().lower()
    if n in ("1", "x", "2"):
        return "X" if n == "x" else n.upper()
    if n in _ALT_DRAW:
        return "X"
    if n in _OU_OVER or n.startswith("над ") or n.startswith("over "):
        return "over"
    if n in _OU_UNDER or n.startswith("под ") or n.startswith("under "):
        return "under"
    if n in ("yes", "да"):
        return "yes"
    if n in ("no", "не"):
        return "no"
    return normalize_text(name).replace(" ", "_")[:32] or "unknown"


def _altenar_line_from_outcome(name: str) -> str | None:
    n = name.strip().lower()
    for prefix in ("над ", "под ", "over ", "under "):
        if n.startswith(prefix):
            return n[len(prefix) :].strip()
    return None


def _altenar_family(type_id: int | None, name: str) -> str:
    nl = normalize_text(name)
    if type_id == 1 or nl == "1x2":
        return "match_1x2"
    if type_id == 18 or _ALT_GOALS.match(name.strip()):
        return "total_goals"
    if type_id == 166 or _ALT_CORNERS.match(name.strip()):
        return "total_corners"
    if _ALT_CORNERS.match(name.strip()) or "корнер" in nl:
        return "total_corners"
    if type_id == 10 or "handicap" in nl or "хендикап" in nl:
        return "handicap"
    if type_id == 29 or ("двата отбора" in nl and "отбел" in nl):
        return "btts"
    if type_id == 26 or "both teams" in nl or "и двата" in nl:
        return "btts"
    return f"altenar_{type_id}" if type_id else "other"


def _pair_altenar_ou_markets(
    m: dict[str, Any],
    odds_by_id: dict[int, dict],
    bookmaker_slug: str,
    family: str,
    period: str,
    type_id: int | None,
) -> list[ParsedMarket]:
    """Pair Over/Under selections by line (Altenar splits them into separate groups)."""
    by_line: dict[str, dict[str, ParsedOutcome]] = {}
    for group in m.get("desktopOddIds") or []:
        for oid in group:
            o = odds_by_id.get(oid)
            if not o:
                continue
            label = str(o.get("name", ""))
            odd = parse_odd(o.get("price"))
            if not odd:
                continue
            line = _altenar_line_from_outcome(label)
            role = _altenar_outcome_role(label)
            if not line or role not in ("over", "under"):
                continue
            by_line.setdefault(line, {})[role] = ParsedOutcome(role=role, name=label, odd=odd)

    raw_name = (m.get("name") or "").strip()
    markets: list[ParsedMarket] = []
    for line, roles in by_line.items():
        if "over" not in roles or "under" not in roles:
            continue
        markets.append(
            ParsedMarket(
                external_id=f"{m.get('id')}:{line}",
                market_name=f"{raw_name} {line}",
                platform="altenar",
                bookmaker_slug=bookmaker_slug,
                family=family,
                period=period,
                scope="match",
                line=line,
                outcomes=[roles["over"], roles["under"]],
                provider_template=f"typeId:{type_id}",
                specifiers={"type_id": type_id},
                raw_payload=m,
            )
        )
    return markets


def _dedupe_parsed(markets: list[ParsedMarket]) -> list[ParsedMarket]:
    seen: set[str] = set()
    out: list[ParsedMarket] = []
    for m in markets:
        if m.external_id in seen:
            continue
        seen.add(m.external_id)
        out.append(m)
    return out


def extract_all_altenar_markets(data: dict[str, Any], bookmaker_slug: str) -> list[ParsedMarket]:
    markets: list[ParsedMarket] = []
    odds_by_id = {o["id"]: o for o in data.get("odds", [])}

    for m in data.get("markets", []):
        raw_name = (m.get("name") or "").strip()
        if not raw_name or is_combo_market(raw_name) or is_promo_market(raw_name):
            continue

        type_id = m.get("typeId")
        family = _altenar_family(type_id, raw_name)
        period = detect_period(raw_name)

        if type_id == 18 and _ALT_GOALS.match(raw_name):
            markets.extend(
                _pair_altenar_ou_markets(m, odds_by_id, bookmaker_slug, family, period, type_id)
            )
            continue

        if type_id == 166 and _ALT_CORNERS.match(raw_name):
            markets.extend(
                _pair_altenar_ou_markets(m, odds_by_id, bookmaker_slug, family, period, type_id)
            )
            continue

        # Altenar packs multiple lines in desktopOddIds groups
        groups = m.get("desktopOddIds") or []
        if not groups:
            continue

        # BTTS-style: one outcome per group (Да / Не in separate groups)
        if all(len(g) == 1 for g in groups) and len(groups) >= 2:
            merged: list[ParsedOutcome] = []
            for group in groups:
                oid = group[0]
                o = odds_by_id.get(oid)
                if not o:
                    continue
                label = str(o.get("name", ""))
                odd = parse_odd(o.get("price"))
                if not odd:
                    continue
                role = _altenar_outcome_role(label)
                merged.append(ParsedOutcome(role=role, name=label, odd=odd))
            merged_roles = {o.role for o in merged}
            if merged_roles == {"yes", "no"} and family == "btts":
                markets.append(
                    ParsedMarket(
                        external_id=f"{m.get('id')}",
                        market_name=raw_name,
                        platform="altenar",
                        bookmaker_slug=bookmaker_slug,
                        family=family,
                        period=period,
                        scope="match",
                        line=None,
                        outcomes=merged,
                        provider_template=f"typeId:{type_id}",
                        raw_payload=m,
                    )
                )
                continue
            if merged_roles == {"1", "X", "2"} and family == "match_1x2":
                merged = sorted(merged, key=lambda o: ("1", "X", "2").index(o.role))
                markets.append(
                    ParsedMarket(
                        external_id=f"{m.get('id')}",
                        market_name=raw_name,
                        platform="altenar",
                        bookmaker_slug=bookmaker_slug,
                        family=family,
                        period=period,
                        scope="match",
                        line=None,
                        outcomes=merged,
                        provider_template=f"typeId:{type_id}",
                        raw_payload=m,
                    )
                )
                continue

        if family == "match_1x2" and len(groups) == 1:
            outs = []
            for oid in groups[0]:
                o = odds_by_id.get(oid)
                if not o:
                    continue
                label = str(o.get("name", ""))
                odd = parse_odd(o.get("price"))
                if not odd:
                    continue
                role = _altenar_outcome_role(label)
                outs.append(ParsedOutcome(role=role, name=label, odd=odd))
            if len(outs) >= 2:
                markets.append(
                    ParsedMarket(
                        external_id=f"{m.get('id')}",
                        market_name=raw_name,
                        platform="altenar",
                        bookmaker_slug=bookmaker_slug,
                        family=family,
                        period=period,
                        scope="match",
                        line=None,
                        outcomes=outs,
                        provider_template=f"typeId:{type_id}",
                        raw_payload=m,
                    )
                )
            continue

        # Totals / multi-line: one ParsedMarket per line pair
        for gi, group in enumerate(groups):
            outs: list[ParsedOutcome] = []
            line: str | None = None
            for oid in group:
                o = odds_by_id.get(oid)
                if not o:
                    continue
                label = str(o.get("name", ""))
                odd = parse_odd(o.get("price"))
                if not odd:
                    continue
                extracted_line = _altenar_line_from_outcome(label)
                if extracted_line:
                    line = extracted_line
                role = _altenar_outcome_role(label)
                outs.append(ParsedOutcome(role=role, name=label, odd=odd))

            if len(outs) < 2:
                continue

            roles = {o.role for o in outs}
            if roles == {"over", "under"} and line:
                markets.append(
                    ParsedMarket(
                        external_id=f"{m.get('id')}:{line}",
                        market_name=f"{raw_name} {line}",
                        platform="altenar",
                        bookmaker_slug=bookmaker_slug,
                        family=family,
                        period=period,
                        scope="match",
                        line=line,
                        outcomes=outs,
                        provider_template=f"typeId:{type_id}",
                        specifiers={"group_index": gi},
                        raw_payload=m,
                    )
                )
            elif len(outs) >= 2:
                markets.append(
                    ParsedMarket(
                        external_id=f"{m.get('id')}:g{gi}",
                        market_name=raw_name,
                        platform="altenar",
                        bookmaker_slug=bookmaker_slug,
                        family=family,
                        period=period,
                        scope="match",
                        line=line,
                        outcomes=outs,
                        provider_template=f"typeId:{type_id}",
                        specifiers={"group_index": gi},
                        raw_payload=m,
                    )
                )

    return _dedupe_parsed(markets)


def _efbet_outcome_role(outcome: dict[str, Any]) -> str | None:
    spec_type = outcome.get("specifiers", {}).get("type", [])
    if isinstance(spec_type, list):
        if "competitor1" in spec_type:
            return "1"
        if "draw" in spec_type:
            return "X"
        if "competitor2" in spec_type:
            return "2"
    for field in ("name", "outcomeTemplateName", "originalName"):
        text = str(outcome.get(field) or "").strip().lower()
        if text in ("1",):
            return "1"
        if text in ("x", "равен", "draw", "равенство"):
            return "X"
        if text in ("2",):
            return "2"
        if text in _OU_OVER:
            return "over"
        if text in _OU_UNDER:
            return "under"
        if text in ("yes", "да"):
            return "yes"
        if text in ("no", "не"):
            return "no"
    return None


def _efbet_family(name: str, outcomes: list[dict], original_name: str = "") -> tuple[str, str | None]:
    n = normalize_text(name)
    orig = normalize_text(original_name)
    if "брой корнери" in orig and "полувреме" not in orig and " - " not in orig:
        if re.match(r"^\d+\.?\d*$", name.strip()):
            return "total_corners", name.strip()
    if n in ("краен резултат", "1x2"):
        return "match_1x2", None
    if re.match(r"^\d+\.?\d*$", n):
        return "total_goals", name.strip()
    if "корнер" in n or "corner" in n:
        line_match = re.search(r"(\d+\.?\d*)", name)
        return "total_corners", line_match.group(1) if line_match else None
    if "голов" in n or "goal" in n:
        line_match = re.search(r"(\d+\.?\d*)", name)
        return "total_goals", line_match.group(1) if line_match else None
    if "двата отбора" in n or "и двата" in n or "both teams" in n:
        return "btts", None
    if len(outcomes) == 2:
        roles = [_efbet_outcome_role(o) for o in outcomes]
        if set(r for r in roles if r) == {"over", "under"}:
            return "total", name.strip()
    return "other", None


def extract_all_efbet_markets(event: dict[str, Any], bookmaker_slug: str) -> list[ParsedMarket]:
    markets: list[ParsedMarket] = []

    for m in _iter_efbet_markets(event):
        raw_name = (m.get("name") or "").strip()
        if not raw_name or is_combo_market(raw_name) or is_promo_market(raw_name):
            continue

        outs_raw = m.get("outcomes", []) or []
        outs: list[ParsedOutcome] = []
        for o in outs_raw:
            odd = parse_odd(o.get("odds") or o.get("realOdds"))
            if not odd:
                continue
            role = _efbet_outcome_role(o)
            if not role:
                role = normalize_text(str(o.get("name") or "")).replace(" ", "_")[:32]
            name = str(o.get("name") or role)
            outs.append(ParsedOutcome(role=role, name=name, odd=odd))

        if len(outs) < 2:
            continue

        specifiers = dict(m.get("specifiers") or {})
        original_name = (m.get("originalName") or "").strip()
        if original_name:
            specifiers["original_name"] = original_name

        family, line = _efbet_family(raw_name, outs_raw, original_name)
        period = detect_period(raw_name)

        markets.append(
            ParsedMarket(
                external_id=str(m.get("id") or raw_name),
                market_name=raw_name,
                platform="efbet",
                bookmaker_slug=bookmaker_slug,
                family=family,
                period=period,
                scope="match",
                line=line or raw_name if re.match(r"^\d+\.?\d*$", raw_name) else line,
                outcomes=outs,
                provider_template=str(m.get("marketTypeId") or m.get("typeId") or ""),
                specifiers=specifiers,
                raw_payload=m,
            )
        )

    return markets


def extract_all_sportinno_markets(event: dict[str, Any], bookmaker_slug: str) -> list[ParsedMarket]:
    markets: list[ParsedMarket] = []
    for mt in event.get("marketTypes", []) or []:
        group_name = str(mt.get("name") or "").strip()
        type_id = mt.get("id")
        for m in mt.get("markets", []) or []:
            line = str(m.get("line") or "").strip() or None
            selections = m.get("selections") or []
            outs: list[ParsedOutcome] = []
            for s in selections:
                label = str(s.get("name", "")).strip()
                odd = parse_odd(s.get("odds"))
                if not odd:
                    continue
                role = _altenar_outcome_role(label)
                outs.append(ParsedOutcome(role=role, name=label, odd=odd))
            if len(outs) < 2:
                continue
            roles = {o.role for o in outs}
            if roles == {"over", "under"}:
                family = "total_goals"
            elif roles == {"yes", "no"}:
                family = "btts"
                line = None
            elif roles == {"1", "X", "2"}:
                family = "match_1x2"
                line = None
                outs = sorted(outs, key=lambda o: ("1", "X", "2").index(o.role))
            else:
                continue
            markets.append(
                ParsedMarket(
                    external_id=f"{type_id}:{line or m.get('id')}",
                    market_name=f"{group_name} {line}" if line else group_name,
                    platform="sportinno",
                    bookmaker_slug=bookmaker_slug,
                    family=family,
                    period=detect_period(group_name),
                    scope="match",
                    line=line,
                    outcomes=outs,
                    provider_template=f"typeId:{type_id}",
                    specifiers={"group_name": group_name, "type_id": type_id},
                    raw_payload=m,
                )
            )
    return markets


def extract_all_markets(
    platform: str,
    payload: dict[str, Any],
    bookmaker_slug: str,
) -> list[ParsedMarket]:
    if platform == "egt":
        return extract_all_egt_markets(payload, bookmaker_slug)
    if platform == "altenar":
        return extract_all_altenar_markets(payload, bookmaker_slug)
    if platform == "efbet":
        return extract_all_efbet_markets(payload, bookmaker_slug)
    if platform == "sportinno":
        event = payload
        if "marketTypes" not in event and "sportEvent" in event:
            event = event["sportEvent"]
        return extract_all_sportinno_markets(event, bookmaker_slug)
    return []
