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


def _parse_odd(value: Any) -> float | None:
    if value is None:
        return None
    try:
        o = float(value)
        return o if o > 1.0 else None
    except (TypeError, ValueError):
        return None


def extract_egt_markets(data: dict[str, Any]) -> list[MarketOdds]:
    markets: list[MarketOdds] = []
    markets_data = data.get("marketsData") or {}
    for m in markets_data.values():
        name = (m.get("name") or "").lower()
        template = m.get("radarMarketTemplateName")
        outcomes_raw = m.get("outcomes") or []
        if "enhanced" in name:
            continue

        if template == "3Way" and "full time result" in name:
            outs = []
            for o in outcomes_raw:
                label = str(o.get("name", ""))
                odd = _parse_odd(o.get("odds"))
                if odd and label in ("1", "X", "2"):
                    outs.append(OutcomeOdd(name=label, odd=odd))
            if len(outs) == 3:
                markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))

        if "total goals" in name or "брой голове" in name:
            line = str(m.get("specialOddsValue") or m.get("line") or "")
            if "2.5" in line or "2.5" in name:
                outs = _extract_over_under(outcomes_raw)
                if outs:
                    markets.append(
                        MarketOdds(market_code="GOALS_OU_25", outcomes=outs, line="2.5")
                    )

        if "corner" in name or "корнер" in name:
            line = str(m.get("specialOddsValue") or m.get("line") or name)
            outs = _extract_over_under(outcomes_raw)
            if not outs:
                continue
            if "8.5" in line:
                markets.append(
                    MarketOdds(market_code="CORNERS_OU_85", outcomes=outs, line="8.5")
                )
            elif "9.5" in line:
                markets.append(
                    MarketOdds(market_code="CORNERS_OU_95", outcomes=outs, line="9.5")
                )
    return markets


def _extract_over_under(outcomes_raw: list[dict]) -> list[OutcomeOdd]:
    over = under = None
    for o in outcomes_raw:
        name = str(o.get("name", "")).lower()
        odd = _parse_odd(o.get("odds"))
        if not odd:
            continue
        if name in ("over", "над") or name.startswith("over") or "над" in name:
            over = OutcomeOdd(name="Over", odd=odd)
        elif name in ("under", "под") or name.startswith("under") or "под" in name:
            under = OutcomeOdd(name="Under", odd=odd)
    if over and under:
        return [over, under]
    return []


def extract_altenar_markets(data: dict[str, Any]) -> list[MarketOdds]:
    markets: list[MarketOdds] = []
    odds_by_id = {o["id"]: o for o in data.get("odds", [])}

    for m in data.get("markets", []):
        mname = (m.get("name") or "").lower()
        type_id = m.get("typeId")

        if type_id == 1 and mname == "1x2":
            outs = _altenar_main_odds(m, odds_by_id)
            if len(outs) == 3:
                markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))

        if type_id == 12 or "total" in mname or "голове" in mname:
            sv = str(m.get("sv") or "")
            if "2.5" in sv:
                outs = _altenar_ou_market(m, odds_by_id)
                if outs:
                    markets.append(
                        MarketOdds(market_code="GOALS_OU_25", outcomes=outs, line="2.5")
                    )

        if "corner" in mname or "корнер" in mname or type_id == 166:
            sv = str(m.get("sv") or mname)
            outs = _altenar_ou_market(m, odds_by_id)
            if not outs:
                continue
            if "8.5" in sv:
                markets.append(
                    MarketOdds(market_code="CORNERS_OU_85", outcomes=outs, line="8.5")
                )
            elif "9.5" in sv:
                markets.append(
                    MarketOdds(market_code="CORNERS_OU_95", outcomes=outs, line="9.5")
                )

    # Top-level odds scan for totals/corners lines
    for o in data.get("odds", []):
        name = str(o.get("name", "")).lower()
        sv = str(o.get("sv") or "")
        odd = _parse_odd(o.get("price"))
        if not odd:
            continue
        # paired by typeId groups handled above; skip orphan singles
        _ = (name, sv)

    return markets


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


def _altenar_ou_market(market: dict, odds_by_id: dict) -> list[OutcomeOdd]:
    ids = [i for group in market.get("desktopOddIds", []) for i in group]
    over = under = None
    for oid in ids:
        o = odds_by_id.get(oid)
        if not o:
            continue
        name = str(o.get("name", "")).lower()
        odd = _parse_odd(o.get("price"))
        if not odd:
            continue
        if "над" in name or "over" in name:
            over = OutcomeOdd(name="Over", odd=odd)
        elif "под" in name or "under" in name:
            under = OutcomeOdd(name="Under", odd=odd)
    if over and under:
        return [over, under]
    return []


def extract_efbet_markets(event: dict[str, Any]) -> list[MarketOdds]:
    markets: list[MarketOdds] = []
    for m in event.get("markets", []):
        name = (m.get("name") or "").lower()
        outs_raw = m.get("outcomes", [])
        if "краен" in name:
            outs = []
            for i, o in enumerate(outs_raw[:3]):
                label = str(o.get("name", ""))
                odd = _parse_odd(o.get("odds") or o.get("realOdds"))
                if not odd:
                    continue
                if label in ("1", "X", "2"):
                    outs.append(OutcomeOdd(name=label, odd=odd))
                elif "равен" in label.lower():
                    outs.append(OutcomeOdd(name="X", odd=odd))
                else:
                    outs.append(OutcomeOdd(name=("1", "X", "2")[i], odd=odd))
            if len(outs) == 3:
                markets.append(MarketOdds(market_code="MATCH_1X2", outcomes=outs))

        if "голове" in name or "goals" in name:
            line = str(m.get("line") or name)
            if "2.5" in line:
                outs = []
                for o in outs_raw:
                    n = str(o.get("name", "")).lower()
                    odd = _parse_odd(o.get("odds"))
                    if not odd:
                        continue
                    if "над" in n:
                        outs.append(OutcomeOdd(name="Over", odd=odd))
                    elif "под" in n:
                        outs.append(OutcomeOdd(name="Under", odd=odd))
                if len(outs) == 2:
                    markets.append(
                        MarketOdds(market_code="GOALS_OU_25", outcomes=outs, line="2.5")
                    )

        if "корнер" in name or "corner" in name:
            line = str(m.get("line") or name)
            outs = []
            for o in outs_raw:
                n = str(o.get("name", "")).lower()
                odd = _parse_odd(o.get("odds"))
                if not odd:
                    continue
                if "над" in n:
                    outs.append(OutcomeOdd(name="Over", odd=odd))
                elif "под" in n:
                    outs.append(OutcomeOdd(name="Under", odd=odd))
            if len(outs) == 2:
                if "8.5" in line:
                    markets.append(
                        MarketOdds(market_code="CORNERS_OU_85", outcomes=outs, line="8.5")
                    )
                elif "9.5" in line:
                    markets.append(
                        MarketOdds(market_code="CORNERS_OU_95", outcomes=outs, line="9.5")
                    )
    return markets


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
    return markets


def _sportinno_ou(selections: list[dict]) -> list[OutcomeOdd] | None:
    over = under = None
    for s in selections:
        name = str(s.get("name", "")).lower()
        odd = _parse_odd(s.get("odds"))
        if not odd:
            continue
        if "над" in name or "over" in name:
            over = OutcomeOdd(name="Over", odd=odd)
        elif "под" in name or "under" in name:
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
