from __future__ import annotations

import re

from rapidfuzz import fuzz

from scraper.v2.canonical import normalize_text

# BG / EN semantic equivalents for cross-bookmaker market name matching
_MARKET_PHRASE_ALIASES: dict[str, str] = {
    "краен резултат": "match_result",
    "full time result": "match_result",
    "match result": "match_result",
    "1x2": "match_result",
    "общ брой голове": "total_goals",
    "общ брои голове": "total_goals",
    "total goals": "total_goals",
    "goal line": "total_goals",
    "match goals": "total_goals",
    "брой голове": "total_goals",
    "брои голове": "total_goals",
    "общ брой корнери": "total_corners",
    "общ брои корнери": "total_corners",
    "total corners": "total_corners",
    "corner line": "total_corners",
    "corners": "total_corners",
    "корнери": "total_corners",
    "общ брой картони": "total_cards",
    "total bookings": "total_cards",
    "total cards": "total_cards",
    "брой картони": "total_cards",
    "картони": "total_cards",
    "1-во полувреме - брой голове": "total_goals_1h",
    "1во полувреме - общ брой голове": "total_goals_1h",
    "1st half - total goals": "total_goals_1h",
    "голове през 1-во полувреме": "total_goals_1h",
    "и двата отбора да отбележат": "btts",
    "both teams to score": "btts",
    "asian handicap": "handicap",
    "хендикап": "handicap",
    "handicap": "handicap",
    "double chance": "double_chance",
    "двоен шанс": "double_chance",
    "draw no bet": "draw_no_bet",
    "без равен": "draw_no_bet",
}

_LINE_PATTERN = re.compile(r"\b(\d+\.?\d*)\b")
_NOISE = re.compile(
    r"\b(pre-match|in-play|enhanced|early payout|0%|margin|марж)\b", re.I
)


def _normalize_market_text(value: str) -> str:
    text = normalize_text(value)
    # NFKD turns Cyrillic й into и + combining mark → "брой" becomes "брои"
    return text.replace("й", "и")


def extract_line_from_name(name: str) -> str | None:
    m = _LINE_PATTERN.search(name)
    return m.group(1) if m else None


def semantic_market_slug(name: str, line: str | None = None) -> str:
    """
    Normalize a market name to a cross-language semantic slug for matching.
    Strips embedded line values so 'Total Goals 2.5' and '2.5' can align.
    """
    text = _normalize_market_text(name)
    text = _NOISE.sub("", text).strip()
    extracted_line = line or extract_line_from_name(text)
    if extracted_line:
        text = text.replace(extracted_line, "").strip()

    for phrase, slug in sorted(_MARKET_PHRASE_ALIASES.items(), key=lambda x: -len(x[0])):
        if phrase in text:
            if extracted_line and slug in (
                "total_goals",
                "total_corners",
                "total_cards",
                "total_goals_1h",
                "handicap",
            ):
                return f"{slug}_{extracted_line}"
            return slug

    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace(" ", "_")[:64] or "unknown"


def market_names_match(name_a: str, name_b: str, line_a: str | None, line_b: str | None) -> bool:
    """Fuzzy cross-language market name equivalence check."""
    if line_a and line_b and line_a != line_b:
        return False

    slug_a = semantic_market_slug(name_a, line_a)
    slug_b = semantic_market_slug(name_b, line_b)
    if slug_a == slug_b:
        return True

    if slug_a.startswith("total_") or slug_b.startswith("total_"):
        if line_a and line_b and line_a == line_b:
            if fuzz.token_set_ratio(slug_a, slug_b) >= 80:
                return True

    return fuzz.token_set_ratio(slug_a, slug_b) >= 88
