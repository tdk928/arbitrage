from __future__ import annotations

from datetime import timedelta

from rapidfuzz import fuzz

from scraper.normalize import canonical_key, normalize_team
from scraper.types import RawFixture

KICKOFF_TOLERANCE = timedelta(hours=2)
FUZZY_THRESHOLD = 88


def fixtures_match(a: RawFixture, b: RawFixture) -> bool:
    if abs(a.kickoff_utc - b.kickoff_utc) > KICKOFF_TOLERANCE:
        return False
    ah, aa = normalize_team(a.home_team), normalize_team(a.away_team)
    bh, ba = normalize_team(b.home_team), normalize_team(b.away_team)
    if not ah or not aa or not bh or not ba:
        return False
    if ah == aa or bh == ba:
        return False
    if ah == bh and aa == ba:
        return True
    score_direct = (
        fuzz.token_sort_ratio(ah, bh) >= FUZZY_THRESHOLD
        and fuzz.token_sort_ratio(aa, ba) >= FUZZY_THRESHOLD
    )
    return score_direct


def group_fixtures(all_fixtures: list[RawFixture]) -> list[list[RawFixture]]:
    groups: list[list[RawFixture]] = []
    used: set[int] = set()
    for i, fx in enumerate(all_fixtures):
        if i in used:
            continue
        group = [fx]
        used.add(i)
        for j, other in enumerate(all_fixtures):
            if j in used or fx.bookmaker_slug == other.bookmaker_slug:
                continue
            if fixtures_match(fx, other):
                group.append(other)
                used.add(j)
        groups.append(group)
    return groups


def pick_canonical(group: list[RawFixture]) -> tuple[str, str, str]:
    """Prefer Latin-script names (efbet/bet365) for display and canonical keys."""

    def name_quality(fx: RawFixture) -> tuple[int, int]:
        text = f"{fx.home_team} {fx.away_team}"
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        return (ascii_chars, len(text))

    anchor = max(group, key=name_quality)
    home, away = anchor.home_team, anchor.away_team
    key = canonical_key(home, away, anchor.kickoff_utc)
    return home, away, key
