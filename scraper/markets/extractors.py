from __future__ import annotations

import re
from typing import Any

from scraper.types import MarketOdds, OutcomeOdd

MARKET_CODES = (
    "MATCH_1X2",
    "GOALS_OU_25",
    "CORNERS_OU_85",
    "CORNERS_OU_95",
)

_PLAIN_OU_OVER = frozenset({"over", "над"})
_PLAIN_OU_UNDER = frozenset({"under", "под"})
_EGT_GOALS_25_NAME = re.compile(r"^total goals 2\.5$", re.I)
_EGT_CORNERS_LINE = re.compile(r"^total corners (8\.5|9\.5)$", re.I)
_ALT_GOALS_TOTAL = re.compile(r"^общ брой(?: голове)?$", re.I)
_ALT_CORNERS_TOTAL = re.compile(r"^общ брой корнери$", re.I)
_LINE_TO_GOALS = {"2.5": "GOALS_OU_25"}
_LINE_TO_CORNERS = {"8.5": "CORNERS_OU_85", "9.5": "CORNERS_OU_95"}
_EFBET_FT_1X2 = re.compile(r"^краен резултат$", re.I)


def _parse_odd(value: Any) -> float | None:
    if value is None:
        return None
    try:
        o = float(value)
        return o if o > 1.0 else None
    except (TypeError, ValueError):
        return None


def _is_egt_promo_1x2(name: str) -> bool:
    """0% margin / early payout promo 1X2 (winbet & inbet EGT)."""
    n = name.lower()
    if "full time result enhanced odds" in n:
        return True
    if "0% марж" in n or "0% margin" in n:
        return True
    if "краен резултат 0% марж" in n:
        return True
    if "ранно изплащане" in n and "марж" in n:
        return True
    return False


def _extract_egt_1x2(outcomes_raw: list[dict]) -> list[OutcomeOdd]:
    outs: list[OutcomeOdd] = []
    for o in outcomes_raw:
        label = str(o.get("name", ""))
        odd = _parse_odd(o.get("odds"))
        if odd and label in ("1", "X", "2"):
            outs.append(OutcomeOdd(name=label, odd=odd))
    return outs if len(outs) == 3 else []


def extract_egt_markets(data: dict[str, Any]) -> list[MarketOdds]:
    markets: list[MarketOdds] = []
    markets_data = data.get("marketsData") or {}
    promo_1x2: list[OutcomeOdd] | None = None
    regular_1x2: list[OutcomeOdd] | None = None

    for m in markets_data.values():
        raw_name = m.get("name") or ""
        name = raw_name.lower()
        template = m.get("radarMarketTemplateName")
        outcomes_raw = m.get("outcomes") or []

        if template == "3Way" and "full time result" in name:
            outs = _extract_egt_1x2(outcomes_raw)
            if outs:
                if _is_egt_promo_1x2(raw_name):
                    promo_1x2 = outs
                elif "enhanced" not in name:
                    regular_1x2 = outs

        if _is_egt_match_total_goals_25(name, template, m):
            outs = _extract_over_under(outcomes_raw)
            if outs:
                markets.append(
                    MarketOdds(market_code="GOALS_OU_25", outcomes=outs, line="2.5")
                )

        corner_match = _EGT_CORNERS_LINE.match((m.get("name") or "").strip())
        if corner_match:
            outs = _extract_over_under(outcomes_raw)
            if outs:
                line = corner_match.group(1)
                code = _LINE_TO_CORNERS[line]
                markets.append(MarketOdds(market_code=code, outcomes=outs, line=line))

    if promo_1x2:
        markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=promo_1x2))
    elif regular_1x2:
        markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=regular_1x2))

    return _dedupe_markets(markets)


def _is_egt_match_total_goals_25(name: str, template: str | None, market: dict) -> bool:
    """Full-match O/U 2.5 only — excludes HT/FT combos and team totals."""
    if template != "total":
        return False
    if _EGT_GOALS_25_NAME.match(name.strip()):
        return True
    line = str(market.get("specialOddsValue") or market.get("line") or "")
    if "брой голове" in name and "2.5" in line:
        return "&" not in name and "half" not in name
    return False


def _extract_over_under(outcomes_raw: list[dict]) -> list[OutcomeOdd]:
    over = under = None
    for o in outcomes_raw:
        name = str(o.get("name", "")).strip().lower()
        odd = _parse_odd(o.get("odds"))
        if not odd:
            continue
        if name in _PLAIN_OU_OVER:
            over = OutcomeOdd(name="Over", odd=odd)
        elif name in _PLAIN_OU_UNDER:
            under = OutcomeOdd(name="Under", odd=odd)
    if over and under:
        return [over, under]
    return []


def extract_altenar_markets(data: dict[str, Any]) -> list[MarketOdds]:
    markets: list[MarketOdds] = []
    odds_by_id = {o["id"]: o for o in data.get("odds", [])}

    for m in data.get("markets", []):
        raw_name = (m.get("name") or "").strip()
        mname = raw_name.lower()
        type_id = m.get("typeId")

        if type_id == 1 and mname == "1x2":
            outs = _altenar_main_odds(m, odds_by_id)
            if len(outs) == 3:
                markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))

        if type_id == 18 and _ALT_GOALS_TOTAL.match(raw_name):
            outs = _altenar_pick_line(m, odds_by_id, "2.5")
            if outs:
                markets.append(MarketOdds(market_code="GOALS_OU_25", outcomes=outs, line="2.5"))

        if _ALT_CORNERS_TOTAL.match(raw_name):
            for line in ("8.5", "9.5"):
                outs = _altenar_pick_line(m, odds_by_id, line)
                if outs:
                    code = _LINE_TO_CORNERS[line]
                    markets.append(MarketOdds(market_code=code, outcomes=outs, line=line))

    return _dedupe_markets(markets)


def _altenar_main_odds(market: dict, odds_by_id: dict) -> list[OutcomeOdd]:
    ids = [i for group in market.get("desktopOddIds", []) for i in group]
    outs = []
    for oid in ids:
        o = odds_by_id.get(oid)
        if not o:
            continue
        label = str(o.get("name", ""))
        if label in ("1", "X", "2", "Равенство"):
            norm = "X" if label == "Равенство" else label
            odd = _parse_odd(o.get("price"))
            if odd:
                outs.append(OutcomeOdd(name=norm, odd=odd))
    return outs


def _altenar_pick_line(market: dict, odds_by_id: dict, line: str) -> list[OutcomeOdd]:
    """Altenar packs many lines in one market — pick e.g. 'Над 2.5' / 'Под 2.5'."""
    line_l = line.lower()
    over = under = None
    for oid in [i for group in market.get("desktopOddIds", []) for i in group]:
        o = odds_by_id.get(oid)
        if not o:
            continue
        name = str(o.get("name", "")).strip().lower()
        odd = _parse_odd(o.get("price"))
        if not odd:
            continue
        if name in (f"над {line_l}", f"over {line_l}"):
            over = OutcomeOdd(name="Over", odd=odd)
        elif name in (f"под {line_l}", f"under {line_l}"):
            under = OutcomeOdd(name="Under", odd=odd)
    if over and under:
        return [over, under]
    return []


def _dedupe_markets(markets: list[MarketOdds]) -> list[MarketOdds]:
    seen: set[str] = set()
    out: list[MarketOdds] = []
    for m in markets:
        if m.market_code in seen:
            continue
        seen.add(m.market_code)
        out.append(m)
    return out


def _iter_efbet_markets(event: dict[str, Any]):
    seen: set[int] = set()
    for m in event.get("markets", []) or []:
        mid = m.get("id")
        if mid is not None:
            if mid in seen:
                continue
            seen.add(mid)
        yield m
    for tab in event.get("marketTabs", []) or []:
        for grp in tab.get("marketGroups", []) or []:
            for m in grp.get("markets", []) or []:
                mid = m.get("id")
                if mid is not None:
                    if mid in seen:
                        continue
                    seen.add(mid)
                yield m


def _is_efbet_full_time_1x2_market(market: dict[str, Any]) -> bool:
    """Only plain full-time 1X2 — not HT/FT, BTTS combos, or early-payout variants."""
    name = (market.get("name") or "").strip()
    original = (market.get("originalName") or name).strip()
    return bool(_EFBET_FT_1X2.match(name) and _EFBET_FT_1X2.match(original))


def _efbet_is_draw_outcome(outcome: dict[str, Any]) -> bool:
    spec_type = outcome.get("specifiers", {}).get("type", [])
    if isinstance(spec_type, list) and "draw" in spec_type:
        return True
    for field in ("name", "outcomeTemplateName", "originalName"):
        text = str(outcome.get(field) or "").strip().lower()
        if text in ("равен", "x", "draw", "равенство"):
            return True
    return False


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
        if text in ("{$competitor1}",):
            return "1"
        if text in ("{$competitor2}",):
            return "2"
    return None


def _efbet_1x2(outs_raw: list[dict]) -> list[OutcomeOdd]:
    if len(outs_raw) != 3:
        return []
    names = [str(o.get("name") or "").strip() for o in outs_raw]
    if len(set(names)) == 1:
        return []

    draw_idx = next((i for i, o in enumerate(outs_raw) if _efbet_is_draw_outcome(o)), None)
    by_role: dict[str, OutcomeOdd] = {}
    for i, o in enumerate(outs_raw):
        odd = _parse_odd(o.get("odds") or o.get("realOdds"))
        if not odd:
            return []
        role = _efbet_outcome_role(o)
        if not role and draw_idx == 1:
            if i == 0:
                role = "1"
            elif i == 2:
                role = "2"
        if not role:
            return []
        if role in by_role:
            return []
        by_role[role] = OutcomeOdd(name=role, odd=odd)

    if set(by_role) != {"1", "X", "2"}:
        return []
    return [by_role["1"], by_role["X"], by_role["2"]]


def extract_efbet_markets(event: dict[str, Any]) -> list[MarketOdds]:
    markets: list[MarketOdds] = []
    for m in _iter_efbet_markets(event):
        mname = (m.get("name") or "").strip()
        mname_l = mname.lower()
        outs_raw = m.get("outcomes", []) or []

        if _is_efbet_full_time_1x2_market(m):
            outs = _efbet_1x2(outs_raw)
            if outs:
                markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))

        if mname in _LINE_TO_GOALS:
            outs = _extract_over_under(outs_raw)
            if outs:
                markets.append(
                    MarketOdds(market_code=_LINE_TO_GOALS[mname], outcomes=outs, line=mname)
                )

        if mname in _LINE_TO_CORNERS:
            outs = _extract_over_under(outs_raw)
            if outs:
                markets.append(
                    MarketOdds(market_code=_LINE_TO_CORNERS[mname], outcomes=outs, line=mname)
                )

    return _dedupe_markets(markets)


def extract_sportinno_markets(event: dict[str, Any]) -> list[MarketOdds]:
    markets: list[MarketOdds] = []
    for mt in event.get("marketTypes", []):
        name = (mt.get("name") or "").lower()
        type_id = mt.get("id")
        for m in mt.get("markets", []):
            selections = m.get("selections", [])
            if type_id == 23 or "краен" in name:
                outs = []
                for s in selections:
                    label = str(s.get("name", ""))
                    odd = _parse_odd(s.get("odds"))
                    if not odd:
                        continue
                    if label in ("1", "X", "2"):
                        outs.append(OutcomeOdd(name=label, odd=odd))
                if len(outs) == 3:
                    markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))

            if type_id == 24 or "голове" in name:
                line = str(m.get("line") or "")
                if "2.5" in line or "2.5" in name:
                    ou = _sportinno_ou(selections)
                    if ou:
                        markets.append(
                            MarketOdds(market_code="GOALS_OU_25", outcomes=ou, line="2.5")
                        )

            if type_id == 134 or "корнер" in name:
                line = str(m.get("line") or "")
                ou = _sportinno_ou(selections)
                if not ou:
                    continue
                if "8.5" in line:
                    markets.append(
                        MarketOdds(market_code="CORNERS_OU_85", outcomes=ou, line="8.5")
                    )
                elif "9.5" in line:
                    markets.append(
                        MarketOdds(market_code="CORNERS_OU_95", outcomes=ou, line="9.5")
                    )
    return _dedupe_markets(markets)


def _sportinno_ou(selections: list[dict]) -> list[OutcomeOdd] | None:
    over = under = None
    for s in selections:
        name = str(s.get("name", "")).strip().lower()
        odd = _parse_odd(s.get("odds"))
        if not odd:
            continue
        if name in _PLAIN_OU_OVER:
            over = OutcomeOdd(name="Over", odd=odd)
        elif name in _PLAIN_OU_UNDER:
            under = OutcomeOdd(name="Under", odd=odd)
    if over and under:
        return [over, under]
    return None


def _fractional_to_decimal(value: str) -> float | None:
    if "/" not in value:
        return _parse_odd(value)
    num, den = value.split("/", 1)
    try:
        return round(1 + int(num) / int(den), 3)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def extract_bet365_markets_from_html(html: str) -> list[MarketOdds]:
    """Best-effort 1X2 from hub row; extended markets rarely in hub HTML."""
    markets: list[MarketOdds] = []

    frac = re.findall(r'name="([12X])\s+(\d+/\d+)"', html)
    if len(frac) >= 3:
        outs = []
        for label, f in frac[:3]:
            odd = _fractional_to_decimal(f)
            if odd:
                outs.append(OutcomeOdd(name=label, odd=odd))
        if len(outs) == 3:
            markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))
            return markets

    # Hub pods expose odds as fractional values in fxt-Odd cells.
    inline = re.findall(r">\s*(\d+/\d+)\s*<", html)
    if len(inline) >= 3:
        outs = []
        for label, raw in zip(["1", "X", "2"], inline[:3]):
            odd = _fractional_to_decimal(raw)
            if odd:
                outs.append(OutcomeOdd(name=label, odd=odd))
        if len(outs) == 3:
            markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))
            return markets

    # Pipe-delimited hub text: Mexico|South Africa|date|1|4/9|X|16/5|2|13/2
    parts = re.sub(r"<[^>]+>", "|", html).split("|")
    parts = [p.strip() for p in parts if p.strip()]
    for i, part in enumerate(parts):
        if part not in ("1", "X", "2"):
            continue
        try:
            odds_raw = [parts[i + 1], parts[i + 3], parts[i + 5]]
            labels = ["1", "X", "2"]
        except IndexError:
            continue
        outs = []
        for label, raw in zip(labels, odds_raw):
            odd = _fractional_to_decimal(raw)
            if odd:
                outs.append(OutcomeOdd(name=label, odd=odd))
        if len(outs) == 3:
            markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))
            break
    return markets


def extract_markets_from_payload(platform: str, payload: dict[str, Any]) -> list[MarketOdds]:
    if platform == "egt":
        return extract_egt_markets(payload)
    if platform == "altenar":
        return extract_altenar_markets(payload)
    if platform == "efbet":
        return extract_efbet_markets(payload)
    if platform == "sportinno":
        return extract_sportinno_markets(payload)
    return []
