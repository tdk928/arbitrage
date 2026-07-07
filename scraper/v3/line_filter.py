from __future__ import annotations

import re

_QUARTER_LINE = re.compile(r"\.(25|75)$")


def is_half_line(line: str | None) -> bool:
    """
    Accept 0.5, 1.5, 2.5, 5.5, 6.5 ...
    Reject .25/.75 and whole numbers 1, 2, 3 ...
    """
    if not line:
        return False
    text = str(line).strip().replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        return False
    if value <= 0:
        return False
    if _QUARTER_LINE.search(text):
        return False
    return abs(value * 2 - round(value * 2)) < 1e-9 and int(round(value * 2)) % 2 == 1
